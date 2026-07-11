import time
from collections import OrderedDict
from functools import wraps
import inspect

from app.config import Config


# Bounded LRU + TTL cache. Uses an OrderedDict so the least-recently-used
# entry can be evicted in O(1) once the cache exceeds CACHE_MAX_SIZE. This
# prevents unbounded memory growth under sustained/variable query load.
_CACHE: "OrderedDict[tuple, tuple[float, object]]" = OrderedDict()
_MAX_SIZE = Config.CACHE_MAX_SIZE


def _get(key):
    """Return cached value if present and unexpired, else None. Refreshes LRU order."""
    entry = _CACHE.get(key)
    if entry is None:
        return None
    exp, value = entry
    if exp <= time.time():
        # Expired — drop it.
        _CACHE.pop(key, None)
        return None
    # Mark as most-recently-used.
    _CACHE.move_to_end(key)
    return value


def _set(key, value, ttl):
    """Store value with TTL and evict the oldest entries beyond the size limit."""
    _CACHE[key] = (time.time() + ttl, value)
    _CACHE.move_to_end(key)
    while len(_CACHE) > _MAX_SIZE:
        _CACHE.popitem(last=False)  # Evict least-recently-used.


def cached(ttl: int = 3600):
    """Bounded in-memory TTL + LRU cache decorator.

    Works for both sync and async functions. Uses `inspect.iscoroutinefunction`
    to detect async functions so we don't accidentally cache coroutine objects
    (which cannot be awaited more than once).

    Key is built from function module/name and args/kwargs. The cache is bounded
    to `Config.CACHE_MAX_SIZE` entries; the least-recently-used entry is evicted
    when the limit is exceeded.
    """

    def decorator(fn):
        if inspect.iscoroutinefunction(fn):
            @wraps(fn)
            async def async_wrapper(*args, **kwargs):
                key = (fn.__module__, fn.__name__, args, tuple(sorted(kwargs.items())))
                value = _get(key)
                if value is not None:
                    return value
                value = await fn(*args, **kwargs)
                if value is not None:
                    _set(key, value, ttl)
                return value

            return async_wrapper
        else:
            @wraps(fn)
            def sync_wrapper(*args, **kwargs):
                key = (fn.__module__, fn.__name__, args, tuple(sorted(kwargs.items())))
                value = _get(key)
                if value is not None:
                    return value
                value = fn(*args, **kwargs)
                if value is not None:
                    _set(key, value, ttl)
                return value

            return sync_wrapper

    return decorator
