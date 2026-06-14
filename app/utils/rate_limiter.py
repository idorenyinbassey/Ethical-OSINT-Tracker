"""Rate limiting utility with in-memory fallback."""
import time
import threading
from collections import defaultdict
from typing import Dict, Tuple

# In-memory store: {key: (count, window_start_time)}
_rate_store: Dict[str, Tuple[int, float]] = {}
_lock = threading.Lock()


def check_rate_limit(
    key: str,
    max_requests: int = 10,
    window_seconds: int = 60,
) -> Tuple[bool, int]:
    """Check if a request is within rate limit. Thread-safe."""
    now = time.time()

    with _lock:
        if key not in _rate_store:
            _rate_store[key] = (1, now)
            return True, max_requests - 1

        count, window_start = _rate_store[key]

        if now - window_start >= window_seconds:
            _rate_store[key] = (1, now)
            return True, max_requests - 1

        if count < max_requests:
            _rate_store[key] = (count + 1, window_start)
            return True, max_requests - (count + 1)

        return False, 0


class RateLimiter:
    """Simple per-key in-memory rate limiter."""

    def __init__(self, key: str, max_calls: int = 100, period: int = 3600):
        self._key = key
        self._max_calls = max_calls
        self._period = period

    def allow(self) -> bool:
        allowed, _ = check_rate_limit(self._key, self._max_calls, self._period)
        return allowed


def get_rate_limit_key(user_id: int | None, resource: str) -> str:
    """Generate rate limit key for user + resource."""
    try:
        if user_id is not None:
            return f"user:{user_id}:{resource}"
    except Exception:
        pass
    return f"anon:{resource}"
