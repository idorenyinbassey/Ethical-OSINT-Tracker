"""Service client error handling & logging (Issue #16)."""
import logging

import httpx

from app.services import darkweb_client


class _RaisingClient:
    """Fake httpx.Client context manager whose .get raises TimeoutException."""

    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def get(self, *args, **kwargs):
        raise httpx.TimeoutException("simulated timeout")


def test_timeout_logs_and_returns_structured_error(monkeypatch, caplog):
    monkeypatch.setattr(darkweb_client.httpx, "Client", _RaisingClient)

    with caplog.at_level(logging.ERROR):
        # Unique query so the @cached decorator never serves a stale result.
        result = darkweb_client.search_ahmia("unique-timeout-probe-xyz")

    assert result["error_type"] == "timeout"
    assert result["results"] == []
    # A server-side log line was emitted.
    assert any(r.levelno >= logging.ERROR for r in caplog.records)


def test_error_response_has_no_raw_exception_text(monkeypatch):
    monkeypatch.setattr(darkweb_client.httpx, "Client", _RaisingClient)
    result = darkweb_client.search_ahmia("another-unique-probe-abc")
    # The generic message must not leak the raw exception string.
    assert "simulated timeout" not in result.get("error", "")
