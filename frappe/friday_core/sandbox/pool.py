# Copyright (c) 2026, Friday Labs and contributors
# For license information, please see license.txt

"""
Warm container pool — amortises Docker cold-start latency.

Phase 1: this is a no-op stub. pool.acquire() always returns None,
causing runner.py to cold-spawn. pool.release() is a no-op.

Phase 1.5: replace with a real pool manager that:
- Keeps N idle containers warm (pre-spawned, suspended)
- On acquire: Resume a warm container, reset env, inject new payload
- On release: Return container to pool (cleared and re-suspended)
  instead of destroying it
- Tracks pool size, queue depth, and hit/miss ratio

The execute() interface does NOT change — callers see only SandboxResult.
The pool is an optimisation below that interface.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from frappe.friday_core.sandbox.runner import SandboxResult


@dataclass
class PoolConfig:
    """Configuration for the warm pool (Phase 1.5 wiring)."""
    min_idle: int = 5
    max_idle: int = 20
    max_age_seconds: int = 3600  # 1 hour
    resize_interval_seconds: int = 60


def acquire(pool: "PoolConfig | None" = None) -> "str | None":
    """
    Acquire a warm container from the pool.

    Phase 1: always returns None (cold-spawn path).
    Phase 1.5: returns a container_id from the pool, or None on miss.
    """
    return None


def release(container_id: str, pool: "PoolConfig | None" = None) -> None:
    """
    Return a container to the pool after execution.

    Phase 1: no-op.
    Phase 1.5: resets env, wipes /tmp, re-suspends, returns to pool.
    """
    pass


def pool_stats() -> dict:
    """
    Return current pool instrumentation.

    Phase 1: all counters at zero.
    Phase 1.5: real gauge values.
    """
    return {
        "pool_size": 0,
        "idle_count": 0,
        "acquire_total": 0,
        "cold_spawn_total": 0,
        "hit_ratio": 0.0,
    }


__all__ = ["PoolConfig", "acquire", "release", "pool_stats"]
