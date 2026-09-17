"""app.services.paste_client — paste-dump site search (psbdmp.ws by
default), following the hibp_client-shaped None/[]/list contract."""
from types import SimpleNamespace
from unittest.mock import patch
from app.services import paste_client


def _cfg(enabled=True, api_key=None, base_url=None):
    return SimpleNamespace(is_enabled=enabled, api_key=api_key, base_url=base_url)


class _FakeResponse:
    def __init__(self, json_data, status_code=200):
        self._json = json_data
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            import httpx
            raise httpx.HTTPStatusError("error", request=None, response=self)

    def json(self):
        return self._json


class _FakeClient:
    def __init__(self, get_impl):
        self._get_impl = get_impl

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def get(self, url, **kwargs):
        return self._get_impl(url, **kwargs)


def _client_factory(get_impl):
    def factory(timeout=10):
        return _FakeClient(get_impl)
    return factory


def test_check_pastes_returns_none_when_not_configured():
    with patch.object(paste_client, "get_by_service", return_value=None):
        assert paste_client.check_pastes("nobody-query-1@example.com") is None


def test_check_pastes_returns_none_when_disabled():
    with patch.object(paste_client, "get_by_service", return_value=_cfg(enabled=False)):
        assert paste_client.check_pastes("nobody-query-2@example.com") is None


def test_check_pastes_returns_empty_list_for_zero_hits():
    def get_impl(url, **kwargs):
        return _FakeResponse({"data": []})

    with patch.object(paste_client, "get_by_service", return_value=_cfg()), \
         patch.object(paste_client, "get_http_client", _client_factory(get_impl)):
        result = paste_client.check_pastes("zero-hits-query@example.com")

    assert result == []


def test_check_pastes_returns_hits():
    def get_impl(url, **kwargs):
        assert "hits-query" in url
        return _FakeResponse({"data": [{"id": "abc123", "time": "2024-01-01", "text": "leaked creds here"}]})

    with patch.object(paste_client, "get_by_service", return_value=_cfg()), \
         patch.object(paste_client, "get_http_client", _client_factory(get_impl)):
        result = paste_client.check_pastes("hits-query@example.com")

    assert result == [{"id": "abc123", "url": "https://pastebin.com/abc123",
                        "date": "2024-01-01", "snippet": "leaked creds here"}]


def test_check_pastes_passes_api_key_when_configured():
    captured = {}

    def get_impl(url, **kwargs):
        captured["params"] = kwargs.get("params")
        return _FakeResponse({"data": []})

    with patch.object(paste_client, "get_by_service", return_value=_cfg(api_key="secret-key")), \
         patch.object(paste_client, "get_http_client", _client_factory(get_impl)):
        paste_client.check_pastes("key-query@example.com")

    assert captured["params"]["key"] == "secret-key"


def test_check_pastes_returns_none_on_http_error():
    def get_impl(url, **kwargs):
        return _FakeResponse({}, status_code=500)

    with patch.object(paste_client, "get_by_service", return_value=_cfg()), \
         patch.object(paste_client, "get_http_client", _client_factory(get_impl)):
        result = paste_client.check_pastes("error-query@example.com")

    assert result is None


def test_check_pastes_returns_none_on_timeout():
    def get_impl(url, **kwargs):
        raise Exception("timed out")

    with patch.object(paste_client, "get_by_service", return_value=_cfg()), \
         patch.object(paste_client, "get_http_client", _client_factory(get_impl)):
        result = paste_client.check_pastes("timeout-query@example.com")

    assert result is None


def test_check_pastes_returns_none_on_malformed_response():
    def get_impl(url, **kwargs):
        return _FakeResponse(["not", "a", "dict"])

    with patch.object(paste_client, "get_by_service", return_value=_cfg()), \
         patch.object(paste_client, "get_http_client", _client_factory(get_impl)):
        result = paste_client.check_pastes("malformed-query@example.com")

    assert result is None
