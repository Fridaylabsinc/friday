# Copyright (c) 2026, Friday Labs and contributors
# For license information, please see license.txt

"""
LLM provider abstraction and Minimax M2 implementation.

PROVIDER INTERFACE
==================

Every provider implements `LLMProvider` — a minimal interface with one method:

    chat(messages, tools=None, model=None) → LLMResponse

The interface is deliberately thin so adding OpenAI / Claude / OpenRouter
is a matter of subclassing and implementing one method.

PROVIDER RESOLUTION
==================

`get_provider_for_profile(profile_name)` is the public entry point:

  1. Read the `Agent Profile` row for `profile_name`.
  2. If `model_provider` is set, load that `LLM Provider` row.
  3. Otherwise, fall back to `Agent Settings.default_provider`.
  4. If neither is set, load the first active `LLM Provider` row (last resort).
  5. Return a provider instance configured from that row.

The returned instance is NOT cached — creating it is cheap and you get a
fresh one per call. All per-request state (auth headers, timeouts) is
set at construction time, not at call time.

ERROR HANDLING
==============

- **401 Invalid credentials** → raises `LLMAuthError`. Callers write a
  clean error to the outbound Chat Message, never crash the gateway.
- **429 Rate limit** → retries up to 3 times with exponential backoff.
- **500/502/503 server error** → retries up to 3 times.
- **Timeout (>30 s)** → treated as an error, same retry logic.
- **After all retries exhausted** → raises `LLMError` with a reason string.
  The gateway catches it and writes a system-error outbound row.

WHAT THIS MODULE DOES NOT DO
=============================

- Does not store API keys. Keys live in `LLM Provider.api_key` (Password
  field) — read at construction time from the DocType row.
- Does not own conversation history. That's managed by `prompt_builder`.
- Does not handle streaming. Streaming (progressive token delivery) is
  deferred until a real-time surface (Telegram, web chat) lands.

SEE ALSO
========
- `docs/contributing/proposals/slice-5-llm-integration.md` §2.1
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any, TypedDict

import frappe
import requests

# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------


class LLMResponse(TypedDict):
    """The result of a successful LLM call."""

    content: str
    finish_reason: str
    usage: dict  # {prompt_tokens, completion_tokens, total_tokens}


class LLMError(Exception):
    """Base exception for provider errors that bubble up to the gateway."""

    pass


class LLMAuthError(LLMError):
    """Raised on 401 — invalid or missing API key."""

    pass


# ---------------------------------------------------------------------------
# Abstract interface
# ---------------------------------------------------------------------------


class LLMProvider(ABC):
    """Abstract base for all LLM provider adapters."""

    @abstractmethod
    def chat(
        self,
        messages: list[dict],  # [{"role": "system"|"user"|"assistant", "content": str}]
        tools: list[dict] | None = None,
        model: str | None = None,
    ) -> LLMResponse:
        """
        Send a chat completion request and return the response.

        Arguments:
          - `messages` — the full prompt (system + history + current message).
          - `tools` — OpenAI-format tool definitions, or None for chat-only.
          - `model` — override the provider's default model, or None to use it.

        Returns `LLMResponse`.
        Raises `LLMAuthError` on 401, `LLMError` on other failures.
        """
        ...

    @abstractmethod
    def get_default_model(self) -> str:
        """Return the provider's default model identifier."""
        ...


# ---------------------------------------------------------------------------
# Minimax M2 implementation
# ---------------------------------------------------------------------------


class MinimixProvider(LLMProvider):
    """Minimax M2 chat completions adapter.

    API reference:
    https://www.minimaxi.com/document/Guides/Chat Completion/V2/text/chat

    The API is OpenAI-compatible with minor differences:
      - Auth: Bearer token in Authorization header.
      - Endpoint: https://api.minimax.chat/v1/text/chatcompletion_v2
      - Tool calling: supported via the `tools` parameter.
      - Response: similar shape to OpenAI but model_name in response differs.
    """

    TIMEOUT_SECONDS = 30
    MAX_RETRIES = 3

    def __init__(self, api_key: str, default_model: str, base_url: str | None = None):
        self.api_key = api_key
        self.default_model = default_model
        self.base_url = (base_url or "https://api.minimax.chat").rstrip("/")

    def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        model: str | None = None,
    ) -> LLMResponse:
        model = model or self.default_model
        url = f"{self.base_url}/v1/text/chatcompletion_v2"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
        }
        if tools:
            payload["tools"] = tools

        last_exc: Exception | None = None
        for attempt in range(self.MAX_RETRIES):
            try:
                response = requests.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=self.TIMEOUT_SECONDS,
                )
                if response.status_code == 401:
                    raise LLMAuthError(
                        f"Minimax auth failed (401). Check the API key in "
                        f"the LLM Provider DocType."
                    )
                if response.status_code == 429:
                    # Rate limited — back off and retry.
                    sleep_time = 2 ** attempt
                    time.sleep(sleep_time)
                    continue
                if response.status_code >= 500:
                    # Server error — retry.
                    sleep_time = 2 ** attempt
                    time.sleep(sleep_time)
                    continue
                response.raise_for_status()
                data = response.json()
                return self._parse_response(data)

            except requests.exceptions.Timeout as exc:
                last_exc = exc
                sleep_time = 2**attempt
                time.sleep(sleep_time)
            except requests.exceptions.RequestException as exc:
                last_exc = exc
                sleep_time = 2**attempt
                time.sleep(sleep_time)

        # All retries exhausted.
        raise LLMError(
            f"Minimax call failed after {self.MAX_RETRIES} retries. "
            f"Last error: {last_exc}"
        )

    def get_default_model(self) -> str:
        return self.default_model

    # -------------------------------------------------------------------------
    # Internal
    # -------------------------------------------------------------------------

    def _parse_response(self, data: dict) -> LLMResponse:
        """Extract the assistant's text from a Minimax V2 response dict."""
        choices = data.get("choices", [])
        if not choices:
            raise LLMError("Minimax response has no choices: " + str(data))

        choice = choices[0]
        finish_reason = choice.get("finish_reason", "stop")

        # Minimax returns message.content directly.
        message = choice.get("message", {})
        content = message.get("content", "")

        # Usage block.
        usage = data.get("usage", {})
        return LLMResponse(
            content=content or "",
            finish_reason=finish_reason,
            usage={
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            },
        )


# ---------------------------------------------------------------------------
# Provider resolution
# ---------------------------------------------------------------------------


def get_provider_for_profile(profile_name: str) -> LLMProvider:
    """Return the configured LLM provider for the given Agent Profile.

    Resolution order:
      1. `Agent Profile.model_provider` link → `LLM Provider` row.
      2. `Agent Settings.default_provider` link → `LLM Provider` row.
      3. First active `LLM Provider` row (last resort).
      4. Raises `LLMError` if no provider is configured.

    The returned provider instance is NOT cached. Construction is cheap
    and all secrets are already in memory from the DocType read.
    """
    provider_row = _resolve_provider_row(profile_name)
    if not provider_row:
        raise LLMError(
            f"No LLM Provider configured for Agent Profile {profile_name!r} "
            f"and no default in Agent Settings. Add at least one active "
            f"LLM Provider row in Desk."
        )

    api_key = _get_api_key(provider_row)
    provider_type = provider_row.get("provider_type") or "minimax"
    default_model = provider_row.get("default_model") or "MiniMax-Standard"
    base_url = provider_row.get("base_url") or None

    if provider_type == "minimax":
        return MinimixProvider(
            api_key=api_key,
            default_model=default_model,
            base_url=base_url,
        )

    # Future: openai → OpenAIProvider(...), etc.
    raise LLMError(f"Unsupported provider_type {provider_type!r}")


def _resolve_provider_row(profile_name: str) -> dict | None:
    """Find the LLM Provider DocType row to use for a profile."""
    # Step 1: Agent Profile.model_provider link.
    profile_model = frappe.db.get_value(
        "Agent Profile", profile_name, "model_provider", as_dict=True
    )
    if profile_model and profile_model.get("model_provider"):
        row = frappe.get_doc("LLM Provider", profile_model["model_provider"])
        if row and row.is_active:
            return row.as_dict()

    # Step 2: Agent Settings singleton.
    if frappe.db.exists("Agent Settings", {"name": "Agent Settings"}):
        default = frappe.db.get_value(
            "Agent Settings",
            "Agent Settings",
            "default_provider",
            as_dict=True,
        )
        if default and default.get("default_provider"):
            try:
                row = frappe.get_doc("LLM Provider", default["default_provider"])
                if row and row.is_active:
                    return row.as_dict()
            except Exception:
                pass

    # Step 3: First active LLM Provider row (last resort).
    rows = frappe.get_all(
        "LLM Provider",
        filters={"is_active": 1},
        order_by="creation asc",
        limit=1,
    )
    if rows:
        return frappe.get_doc("LLM Provider", rows[0]["name"]).as_dict()

    return None


def _get_api_key(provider_row: dict) -> str:
    """Read the API key from an LLM Provider dict.

    The key is stored in a Frappe Password field, which is encrypted at rest.
    Frappe provides `get_password()` to decrypt it at runtime.
    """
    # `get_password()` on a DocType field returns the decrypted value.
    # We reconstruct enough of a doc-like object for get_password to work.
    try:
        doc = frappe.get_doc("LLM Provider", provider_row["name"])
        return doc.get_password("api_key") or ""
    except Exception:
        return ""
