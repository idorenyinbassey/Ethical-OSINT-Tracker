"""Bounded LRU + TTL cache (Issue #10)."""
import time

from app.services import cache


def test_cache_evicts_beyond_max_size(monkeypatch):
    monkeypatch.setattr(cache, "_MAX_SIZE", 3)
    cache._CACHE.clear()

    @cache.cached(ttl=100)
    def double(x):
        return x * 2

    for i in range(10):
        double(i)

    assert len(cache._CACHE) <= 3


def test_cache_returns_cached_value():
    cache._CACHE.clear()
    calls = {"n": 0}

    @cache.cached(ttl=100)
    def expensive(x):
        calls["n"] += 1
        return x + 1

    assert expensive(5) == 6
    assert expensive(5) == 6
    assert calls["n"] == 1  # second call served from cache


def test_cache_expires_after_ttl():
    cache._CACHE.clear()

    @cache.cached(ttl=1)
    def f(x):
        return time.time()

    first = f("k")
    time.sleep(1.1)
    second = f("k")
    assert first != second  # entry expired and was recomputed
