import time
from functools import wraps
import inspect


_CACHE: dict[tuple, tuple[float, object]] = {}


def cached(ttl: int = 3600):
    """Simple in-memory TTL cache decorator.

    Works for both sync and async functions. Uses `inspect.iscoroutinefunction`
    to detect async functions so we don't accidentally cache coroutine objects
    (which cannot be awaited more than once).

    Key is built from function module/name and args/kwargs.
    """

    def decorator(fn):
        if inspect.iscoroutinefunction(fn):
            @wraps(fn)
            async def async_wrapper(*args, **kwargs):
                key = (fn.__module__, fn.__name__, args, tuple(sorted(kwargs.items())))
                now = time.time()
                if key in _CACHE:
                    exp, value = _CACHE[key]
                    if exp > now:
                        return value
                value = await fn(*args, **kwargs)
                _CACHE[key] = (now + ttl, value)
                return value

            return async_wrapper
        else:
            @wraps(fn)
            def sync_wrapper(*args, **kwargs):
                key = (fn.__module__, fn.__name__, args, tuple(sorted(kwargs.items())))
                now = time.time()
                if key in _CACHE:
                    exp, value = _CACHE[key]
                    if exp > now:
                        return value
                value = fn(*args, **kwargs)
                _CACHE[key] = (now + ttl, value)
                return value

            return sync_wrapper

    return decorator
