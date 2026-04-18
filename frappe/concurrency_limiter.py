# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# License: MIT. See LICENSE

"""
Concurrency limiter for expensive whitelisted methods.

Provides a @frappe.concurrent_limit() decorator that limits the number of
simultaneous in-flight executions of a function across all gunicorn workers
using a Redis-backed semaphore (LIST + BLPOP).

Usage::

    @frappe.whitelist(allow_guest=True)
    @frappe.concurrent_limit(limit=3)
    def download_pdf(...):
        ...

"""

from collections.abc import Callable
from functools import wraps

import frappe
from frappe.exceptions import ServiceUnavailableError
from frappe.utils import cint
from frappe.utils.caching import redis_cache

# Default wait timeout (seconds) before returning 503 to the caller.
_DEFAULT_WAIT_TIMEOUT = 10


@redis_cache(shared=True)
def _default_limit() -> int:
	"""Derive a sensible default concurrency limit from the number of gunicorn workers."""
	import multiprocessing

	workers = frappe.conf.get("gunicorn_workers") or (multiprocessing.cpu_count() * 2 + 1)
	return max(1, int(workers) // 2)


def concurrent_limit(limit: int | None = None, wait_timeout: int = _DEFAULT_WAIT_TIMEOUT):
	"""Decorator that limits simultaneous in-flight executions of the wrapped function.

	:param limit: Maximum number of concurrent executions. Defaults to ``gunicorn_workers // 2``
	:param wait_timeout: Seconds to wait for a free slot before returning 503.
	    Defaults to 10 s.  Suppressed for background jobs.
	"""

	def decorator(fn: Callable) -> Callable:
		@wraps(fn)
		def wrapper(*args, **kwargs):
			# Skip concurrency limiting outside of HTTP requests (background jobs,
			# CLI commands, tests that call functions directly, etc.).
			if getattr(frappe.local, "request", None) is None:
				return fn(*args, **kwargs)

			_limit = cint(limit) if limit is not None else _default_limit()
			key = f"concurrency:{fn.__module__}.{fn.__qualname__}"

			token = _acquire(key, _limit, wait_timeout)
			if not token:
				retry_after = max(1, int(wait_timeout))
				if (headers := getattr(frappe.local, "response_headers", None)) is not None:
					headers.set("Retry-After", str(retry_after))
				exc = ServiceUnavailableError(frappe._("Server is busy. Please try again in a few seconds."))
				exc.retry_after = retry_after
				raise exc

			try:
				return fn(*args, **kwargs)
			finally:
				_release(key, token)

		return wrapper

	return decorator


def _ensure_tokens(key: str, limit: int) -> None:
	"""Ensure the token pool is initialized with the correct number of tokens.

	Uses ``SET NX`` on a separate capacity key as an atomic init-once flag so
	the pool is never re-filled just because all tokens are legitimately in use
	(empty list ≠ uninitialised).
	"""
	try:
		cap_key = f"{key}:capacity"

		if not frappe.cache.setnx(cap_key, str(limit)):
			return  # already initialized

		# initialize the token pool
		prefixed = frappe.cache.make_key(key)
		pipe = frappe.cache.pipeline(transaction=True)
		pipe.delete(prefixed)
		for i in range(limit):
			pipe.rpush(prefixed, str(i))
		pipe.execute()
	except Exception:
		frappe.log_error("Concurrency limiter: Failed to initialize tokens")


def _acquire(key: str, limit: int, wait_timeout: float) -> str | None:
	"""Try to acquire a token from the pool.

	For *wait_timeout* ≤ 0: uses LPOP (non-blocking).
	For *wait_timeout* > 0: uses BLPOP (blocks until a token is available or
	the timeout expires).
	"""
	try:
		_ensure_tokens(key, limit)

		def _decode(result):
			return result.decode() if isinstance(result, bytes) else result

		if wait_timeout <= 0:
			result = frappe.cache.lpop(key)
			return _decode(result) if result is not None else None

		# Returns (key_bytes, value_bytes) or None on timeout.
		if result := frappe.cache.blpop(key, timeout=int(wait_timeout)):
			return _decode(result[1])
		return None

	except Exception:
		frappe.log_error("Concurrency limiter: Redis unavailable, skipping limit")
		return "fallback"


def _release(key: str, token: str) -> None:
	"""Return the token to the pool."""
	if token == "fallback":
		return
	try:
		frappe.cache.lpush(key, token)
	except Exception:
		frappe.log_error(f"Concurrency limiter: Failed to release token {token}")
