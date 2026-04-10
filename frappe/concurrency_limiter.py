# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# License: MIT. See LICENSE

"""
Concurrency limiter for expensive whitelisted methods.

Provides a @frappe.concurrent_limit() decorator that limits the number of
simultaneous in-flight executions of a function across all gunicorn workers
using a Redis-backed atomic counter (semaphore).

Usage::

    @frappe.whitelist(allow_guest=True)
    @frappe.concurrent_limit(limit=3)
    def download_pdf(...):
        ...

"""

import time
from collections.abc import Callable
from functools import wraps

import frappe

# Safety TTL (seconds) for the Redis key — prevents leaked semaphore slots if a
# worker crashes mid-request. Should be larger than any realistic execution time.
_SLOT_TTL = 120

# Default wait timeout (seconds) before returning 503 to the caller.
_DEFAULT_WAIT_TIMEOUT = 10

# Polling interval (seconds) while waiting for a slot to open.
_POLL_INTERVAL = 0.25


def _default_limit() -> int:
	"""Derive a sensible default concurrency limit from the number of gunicorn workers."""
	import multiprocessing

	workers = frappe.conf.get("gunicorn_workers") or (multiprocessing.cpu_count() * 2 + 1)
	return max(1, int(workers) // 2)


def concurrent_limit(limit: int | None = None, wait_timeout: int | None = None):
	"""Decorator that limits simultaneous in-flight executions of the wrapped function.

	:param limit: Maximum number of concurrent executions. Defaults to
	    ``gunicorn_workers // 2`` (or the value in ``concurrency_limits`` site config).
	:param wait_timeout: Seconds to wait for a free slot before returning 503.
	    Defaults to 10 s.  Suppressed for background jobs.
	"""

	def decorator(fn: Callable) -> Callable:
		@wraps(fn)
		def wrapper(*args, **kwargs):
			# Skip concurrency limiting outside of HTTP requests (background jobs,
			# CLI commands, tests that call functions directly, etc.).
			if not getattr(frappe.local, "request", None):
				return fn(*args, **kwargs)

			effective_limit = int(limit) if limit is not None else _default_limit()
			effective_wait = (
				wait_timeout
				if wait_timeout is not None
				else frappe.conf.get("concurrency_wait_timeout", _DEFAULT_WAIT_TIMEOUT)
			)

			cache_key = frappe.cache.make_key(f"concurrency:{fn.__module__}.{fn.__qualname__}")

			acquired = _acquire(cache_key, effective_limit, effective_wait)
			if not acquired:
				from frappe.exceptions import ServiceUnavailableError

				retry_after = max(1, int(effective_wait))
				exc = ServiceUnavailableError(frappe._("Server is busy. Please try again in a few seconds."))
				exc.retry_after = retry_after
				raise exc

			try:
				return fn(*args, **kwargs)
			finally:
				_release(cache_key)

		return wrapper

	return decorator


def _acquire(cache_key: str, limit: int, wait_timeout: float) -> bool:
	"""Increment the counter and return True if we got a slot within *wait_timeout* seconds.

	The counter is incremented first; if the new value exceeds *limit* the
	increment is undone and we wait before retrying.  This avoids a separate
	check-then-act race condition — INCRBY is atomic.
	"""
	deadline = time.monotonic() + wait_timeout

	while True:
		try:
			current = frappe.cache.incrby(cache_key, 1)
		except Exception:
			# Redis unavailable — fail open to avoid breaking the endpoint entirely.
			frappe.log_error("Concurrency limiter: Redis unavailable, skipping limit")
			return True

		# Refresh TTL on every successful increment so that a slow request
		# doesn't let the slot expire before it finishes.
		try:
			frappe.cache.expire(cache_key, _SLOT_TTL)
		except Exception:
			pass

		if current <= limit:
			return True

		# Over the limit — give back the slot and wait.
		try:
			frappe.cache.incrby(cache_key, -1)
		except Exception:
			pass

		remaining = deadline - time.monotonic()
		if remaining <= 0:
			return False

		time.sleep(min(_POLL_INTERVAL, remaining))


def _release(cache_key: str) -> None:
	"""Decrement the counter, clamping at 0 to guard against double-release."""
	try:
		new_val = frappe.cache.incrby(cache_key, -1)
		if new_val < 0:
			# Shouldn't happen, but clamp to prevent permanently negative counters.
			frappe.cache.incrby(cache_key, -new_val)
	except Exception:
		pass
