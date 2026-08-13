"""HOS-AUTO-02 R2 — Loop Guard.

Rate limiting, TTL, max depth, max continuations, STOP on repeat failure.
"""
import time
from collections import defaultdict


MAX_DEPTH = 3
MAX_CONTINUATIONS = 3
RATE_LIMIT_WINDOW = 300  # 5 minutes
RATE_LIMIT_MAX = 10

_timestamps = []
_failures: dict[str, int] = defaultdict(int)
_continuations: dict[str, int] = defaultdict(int)


def check_rate_limit() -> bool:
    """True if within rate limit, False if exceeded."""
    global _timestamps
    now = time.time()
    _timestamps = [t for t in _timestamps if now - t < RATE_LIMIT_WINDOW]
    if len(_timestamps) >= RATE_LIMIT_MAX:
        return False
    _timestamps.append(now)
    return True


def check_depth(depth: int) -> bool:
    """True if depth is within bounds."""
    return depth <= MAX_DEPTH


def check_ttl(expires_at: str) -> bool:
    """True if not expired. Assumes ISO format."""
    if not expires_at:
        return True
    try:
        from datetime import datetime, timezone
        expires = datetime.fromisoformat(expires_at)
        return datetime.now(timezone.utc) <= expires
    except (ValueError, TypeError):
        return False


def record_failure(task_id: str) -> bool:
    """Record a failure. Returns True if task should STOP (3 identical failures)."""
    _failures[task_id] += 1
    return _failures[task_id] >= 3


def reset_failures(task_id: str):
    _failures.setdefault(task_id, 0)


def record_continuation(parent_task_id: str) -> bool:
    """Record continuation. Returns True if max exceeded."""
    _continuations[parent_task_id] += 1
    return _continuations[parent_task_id] > MAX_CONTINUATIONS