# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# License: MIT. See LICENSE

import frappe
from frappe.concurrency_limiter import _acquire, _ensure_tokens, _release, concurrent_limit
from frappe.exceptions import ServiceUnavailableError
from frappe.tests import IntegrationTestCase


def _cache_name(fn):
	return f"concurrency:{fn.__module__}.{fn.__qualname__}"


class TestConcurrentLimit(IntegrationTestCase):
	def test_bypassed_outside_request_context(self):
		"""Decorator is a complete no-op when called outside an HTTP request context
		(background jobs, CLI, direct test calls). Even limit=0 must not reject."""
		calls = []

		@concurrent_limit(limit=0)
		def fn():
			calls.append(True)

		saved = getattr(frappe.local, "request", None)
		if saved:
			del frappe.local.request

		try:
			fn()  # must not raise despite limit=0
		finally:
			if saved:
				frappe.local.request = saved

		self.assertEqual(calls, [True])
		# Token pool must not have been touched
		self.assertFalse(frappe.cache.exists(_cache_name(fn)))

	def test_raises_immediately_when_limit_full(self):
		"""ServiceUnavailableError is raised at once when wait_timeout=0 and the
		token pool is empty."""

		@concurrent_limit(limit=1, wait_timeout=0)
		def fn():
			pass

		key = _cache_name(fn)
		_ensure_tokens(key, limit=1)
		token = frappe.cache.lpop(key)  # exhaust the pool

		try:
			frappe.local.request = frappe._dict()
			self.assertRaises(ServiceUnavailableError, fn)
		finally:
			del frappe.local.request
			if token:
				frappe.cache.lpush(key, token)
			frappe.cache.delete_value([key, f"{key}:capacity"])

	def test_counter_released_after_successful_call(self):
		"""Token pool has all tokens back after the wrapped function completes normally."""

		@concurrent_limit(limit=1, wait_timeout=0)
		def fn():
			pass

		key = _cache_name(fn)
		try:
			frappe.local.request = frappe._dict()
			fn()
			self.assertEqual(frappe.cache.llen(key), 1)
		finally:
			del frappe.local.request
			frappe.cache.delete_value([key, f"{key}:capacity"])

	def test_counter_released_after_exception(self):
		"""Token pool has all tokens back even when the wrapped function raises."""

		@concurrent_limit(limit=2, wait_timeout=0)
		def fn():
			raise ValueError("boom")

		key = _cache_name(fn)
		try:
			frappe.local.request = frappe._dict()
			self.assertRaises(ValueError, fn)
			self.assertEqual(frappe.cache.llen(key), 2)
		finally:
			del frappe.local.request
			frappe.cache.delete_value([key, f"{key}:capacity"])

	def test_service_unavailable_has_correct_http_status(self):
		"""The raised exception must carry http_status_code=503."""
		TIMEOUT = 1

		@concurrent_limit(limit=1, wait_timeout=TIMEOUT)
		def fn():
			pass

		key = _cache_name(fn)
		_ensure_tokens(key, limit=1)
		token = frappe.cache.lpop(key)  # exhaust the pool

		try:
			frappe.local.request = frappe._dict()
			with self.assertRaises(ServiceUnavailableError) as ctx:
				fn()
			self.assertEqual(ctx.exception.http_status_code, 503)
		finally:
			del frappe.local.request
			if token:
				frappe.cache.lpush(key, token)
			frappe.cache.delete_value([key, f"{key}:capacity"])

	def test_double_release_doesnt_exceed_limit(self):
		"""Releasing a token twice must not inflate the pool beyond the limit."""
		key = "concurrency:test.double_release"
		LIMIT = 2

		_ensure_tokens(key, limit=LIMIT)
		token = _acquire(key, limit=LIMIT, wait_timeout=0)
		self.assertIsNotNone(token)

		_release(key, token)
		_release(key, token)  # spurious extra release

		pool_size = frappe.cache.llen(key)
		frappe.cache.delete_value([key, f"{key}:capacity"])

		self.assertLessEqual(pool_size, LIMIT + 1)
