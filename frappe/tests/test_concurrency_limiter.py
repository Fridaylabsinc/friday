# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# License: MIT. See LICENSE

import threading
import time

import frappe
from frappe.concurrency_limiter import _acquire, _release, concurrent_limit
from frappe.exceptions import ServiceUnavailableError
from frappe.tests import IntegrationTestCase


def _cache_name(fn):
	return f"concurrency:{fn.__module__}.{fn.__qualname__}"


def _cache_key(fn):
	return frappe.cache.make_key(_cache_name(fn))


class TestConcurrentLimit(IntegrationTestCase):
	def test_bypassed_outside_request_context(self):
		"""Decorator is a complete no-op when called outside an HTTP request context
		(background jobs, CLI, direct test calls). Even limit=0 must not reject."""
		calls = []

		@concurrent_limit(limit=0)
		def fn():
			calls.append(True)

		# Make sure no request is set on this thread
		saved = getattr(frappe.local, "request", None)
		if saved:
			del frappe.local.request

		try:
			fn()  # must not raise despite limit=0
		finally:
			if saved:
				frappe.local.request = saved

		self.assertEqual(calls, [True])
		# Counter must not have been touched
		self.assertFalse(frappe.cache.exists(_cache_key(fn)))

	def test_raises_immediately_when_limit_full(self):
		"""ServiceUnavailableError is raised at once when wait_timeout=0 and the
		slot counter is already at the limit."""

		@concurrent_limit(limit=1, wait_timeout=0)
		def fn():
			pass

		key = _cache_key(fn)
		frappe.cache.incrby(key, 1)  # simulate one in-flight request
		frappe.cache.expire(key, 60)

		try:
			frappe.local.request = frappe._dict()
			self.assertRaises(ServiceUnavailableError, fn)
		finally:
			del frappe.local.request
			frappe.cache.delete(key)

	def test_counter_released_after_successful_call(self):
		"""Slot counter returns to zero after the wrapped function completes normally."""

		@concurrent_limit(limit=1, wait_timeout=0)
		def fn():
			pass

		key = _cache_key(fn)
		try:
			frappe.local.request = frappe._dict()
			fn()
			self.assertEqual(frappe.cache.incrby(_cache_key(fn), 0), 0)
		finally:
			del frappe.local.request
			frappe.cache.delete(key)

	def test_counter_released_after_exception(self):
		"""Slot counter returns to zero even when the wrapped function raises.
		This verifies the finally-block release path."""

		@concurrent_limit(limit=2, wait_timeout=0)
		def fn():
			raise ValueError("boom")

		key = _cache_key(fn)
		try:
			frappe.local.request = frappe._dict()
			self.assertRaises(ValueError, fn)
			self.assertEqual(frappe.cache.incrby(_cache_key(fn), 0), 0)
		finally:
			del frappe.local.request
			frappe.cache.delete(key)

	def test_service_unavailable_has_correct_http_status(self):
		"""The raised exception must carry http_status_code=503."""
		TIMEOUT = 1

		@concurrent_limit(limit=1, wait_timeout=TIMEOUT)
		def fn():
			pass

		key = _cache_key(fn)
		frappe.cache.incrby(key, 1)
		frappe.cache.expire(key, 60)

		try:
			frappe.local.request = frappe._dict()
			with self.assertRaises(ServiceUnavailableError) as ctx:
				fn()
			exc = ctx.exception
			self.assertEqual(exc.http_status_code, 503)
		finally:
			del frappe.local.request
			frappe.cache.delete(key)

	def test_waiter_acquires_slot_when_released(self):
		"""A blocked _acquire call succeeds once a concurrent holder calls _release.
		Tests the polling loop without going through the decorator."""
		key = frappe.cache.make_key("concurrency:test.waiter_acquire")

		# Simulate one in-flight holder
		frappe.cache.incrby(key, 1)
		frappe.cache.expire(key, 60)

		acquired = []

		def release_after_short_delay():
			time.sleep(0.3)
			_release(key)

		releaser = threading.Thread(target=release_after_short_delay, daemon=True)
		releaser.start()

		# wait_timeout=2 — should succeed well within that window
		result = _acquire(key, limit=1, wait_timeout=2)
		acquired.append(result)

		releaser.join()
		frappe.cache.delete(key)

		self.assertTrue(acquired[0])

	def test_counter_clamped_at_zero_on_double_release(self):
		"""Calling _release more times than _acquire must never produce a negative
		counter (which would inflate the effective slot budget)."""
		key = frappe.cache.make_key("concurrency:test.clamp_release")

		frappe.cache.incrby(key, 1)
		_release(key)  # correct release → 0
		_release(key)  # spurious extra release

		counter = frappe.cache.incrby(key, 0)
		frappe.cache.delete(key)

		self.assertGreaterEqual(counter, 0)

	def test_concurrent_threads_respect_limit(self):
		"""Exactly `limit` threads acquire concurrently; the rest are rejected when
		wait_timeout=0.  This exercises the atomic INCRBY semaphore across threads."""
		LIMIT = 2
		TOTAL = 5
		key = frappe.cache.make_key("concurrency:test.thread_limit")

		successes = []
		rejections = []
		lock = threading.Lock()
		barrier = threading.Barrier(TOTAL)

		def attempt():
			barrier.wait()  # all threads race _acquire simultaneously
			if _acquire(key, limit=LIMIT, wait_timeout=0):
				with lock:
					successes.append(1)
				time.sleep(0.05)  # hold the slot briefly
				_release(key)
			else:
				with lock:
					rejections.append(1)

		threads = [threading.Thread(target=attempt, daemon=True) for _ in range(TOTAL)]
		for t in threads:
			t.start()
		for t in threads:
			t.join()

		frappe.cache.delete(key)

		self.assertEqual(len(successes), LIMIT)
		self.assertEqual(len(rejections), TOTAL - LIMIT)
