import time
from functools import wraps


_CACHE: dict[tuple, tuple[float, object]] = {}


def cached(ttl: int = 3600):
    """Simple in-memory TTL cache decorator.

    Key is built from function name and args/kwargs.
    """

    def decorator(fn):
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

        # choose wrapper based on coroutine
        return async_wrapper if hasattr(fn, "__code") and fn.__code__.co_flags & 0x80 else sync_wrapper

    return decorator
