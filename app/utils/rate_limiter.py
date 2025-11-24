"""Rate limiting utility with in-memory fallback."""
import time
from collections import defaultdict
from typing import Dict, Tuple

# In-memory store: {key: (count, window_start_time)}
_rate_store: Dict[str, Tuple[int, float]] = {}
_locks: Dict[str, bool] = defaultdict(bool)

def check_rate_limit(
    key: str,
    max_requests: int = 10,
    window_seconds: int = 60,
) -> Tuple[bool, int]:
    """
    Check if a request is within rate limit.
    
    Args:
        key: Unique identifier (e.g., f"user:{user_id}:domain" or "global:ip")
        max_requests: Maximum requests allowed in window
        window_seconds: Time window in seconds
    
    Returns:
        (allowed: bool, remaining: int)
    """
    now = time.time()
    
    if key not in _rate_store:
        _rate_store[key] = (1, now)
        return True, max_requests - 1
    
    count, window_start = _rate_store[key]
    
    # Reset window if expired
    if now - window_start >= window_seconds:
        _rate_store[key] = (1, now)
        return True, max_requests - 1
    
    # Within window
    if count < max_requests:
        _rate_store[key] = (count + 1, window_start)
        return True, max_requests - (count + 1)
    
    # Rate limit exceeded
    return False, 0


def get_rate_limit_key(user_id: int | None, resource: str) -> str:
    """Generate rate limit key for user + resource.

    Avoid boolean evaluation of reactive Vars by using identity check.
    """
    try:
        # Identity comparison avoids Var __bool__.
        if user_id is not None:
            return f"user:{user_id}:{resource}"
    except Exception:
        # Fall back to anonymous key if anything unexpected.
        pass
    return f"anon:{resource}"
