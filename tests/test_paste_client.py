"""app.services.paste_client — leak search against Hudson Rock's free
Cavalier Community API, following the hibp_client-shaped None/[]/list
contract. Response parsing is deliberately defensive (schema wasn't
independently verified against live traffic), so several plausible
shapes are exercised here rather than just one exact fixture."""
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
        return _FakeResponse({"stealers": []})

    with patch.object(paste_client, "get_by_service", return_value=_cfg()), \
         patch.object(paste_client, "get_http_client", _client_factory(get_impl)):
        result = paste_client.check_pastes("zero-hits-query@example.com")

    assert result == []


def test_check_pastes_uses_email_endpoint_for_email_query():
    captured = {}

    def get_impl(url, **kwargs):
        captured["url"] = url
        captured["params"] = kwargs.get("params")
        return _FakeResponse({"stealers": []})

    with patch.object(paste_client, "get_by_service", return_value=_cfg()), \
         patch.object(paste_client, "get_http_client", _client_factory(get_impl)):
        paste_client.check_pastes("someone@example.com")

    assert "search-by-email" in captured["url"]
    assert captured["params"]["email"] == "someone@example.com"


def test_check_pastes_uses_domain_endpoint_for_domain_query():
    captured = {}

    def get_impl(url, **kwargs):
        captured["url"] = url
        captured["params"] = kwargs.get("params")
        return _FakeResponse({"stealers": []})

    with patch.object(paste_client, "get_by_service", return_value=_cfg()), \
         patch.object(paste_client, "get_http_client", _client_factory(get_impl)):
        paste_client.check_pastes("example-domain-query.com")

    assert "search-by-domain" in captured["url"]
    assert captured["params"]["domain"] == "example-domain-query.com"


def test_check_pastes_uses_username_endpoint_otherwise():
    captured = {}

    def get_impl(url, **kwargs):
        captured["url"] = url
        captured["params"] = kwargs.get("params")
        return _FakeResponse({"stealers": []})

    with patch.object(paste_client, "get_by_service", return_value=_cfg()), \
         patch.object(paste_client, "get_http_client", _client_factory(get_impl)):
        paste_client.check_pastes("plainusername")

    assert "search-by-username" in captured["url"]
    assert captured["params"]["username"] == "plainusername"


def test_check_pastes_returns_hits_with_credentials():
    def get_impl(url, **kwargs):
        return _FakeResponse({
            "stealers": [{
                "stealer_family": "RedLine",
                "date_compromised": "2024-01-01",
                "credentials": [
                    {"url": "https://bank.example/login", "domain": "bank.example",
                     "username": "victim", "password": "hunter2"},
                ],
            }]
        })

    with patch.object(paste_client, "get_by_service", return_value=_cfg()), \
         patch.object(paste_client, "get_http_client", _client_factory(get_impl)):
        result = paste_client.check_pastes("hits-query@example.com")

    assert len(result) == 1
    hit = result[0]
    assert hit["url"] == "https://bank.example/login"
    assert hit["date"] == "2024-01-01"
    assert "RedLine" in hit["snippet"]
    assert "bank.example" in hit["snippet"]
    # never re-surface the actual captured credentials
    assert "victim" not in hit["snippet"]
    assert "hunter2" not in hit["snippet"]


def test_check_pastes_handles_entry_with_no_credentials():
    def get_impl(url, **kwargs):
        return _FakeResponse({
            "stealers": [{"stealer_family": "Vidar", "date_uploaded": "2024-02-02", "credentials": []}]
        })

    with patch.object(paste_client, "get_by_service", return_value=_cfg()), \
         patch.object(paste_client, "get_http_client", _client_factory(get_impl)):
        result = paste_client.check_pastes("no-creds-query@example.com")

    assert len(result) == 1
    assert result[0]["url"] == ""
    assert result[0]["date"] == "2024-02-02"
    assert "Vidar" in result[0]["snippet"]


def test_check_pastes_accepts_bare_list_response():
    def get_impl(url, **kwargs):
        return _FakeResponse([{"stealer_family": "Raccoon", "date_compromised": "2024-03-03", "credentials": []}])

    with patch.object(paste_client, "get_by_service", return_value=_cfg()), \
         patch.object(paste_client, "get_http_client", _client_factory(get_impl)):
        result = paste_client.check_pastes("bare-list-query@example.com")

    assert len(result) == 1
    assert "Raccoon" in result[0]["snippet"]


def test_check_pastes_passes_api_key_when_configured():
    captured = {}

    def get_impl(url, **kwargs):
        captured["params"] = kwargs.get("params")
        return _FakeResponse({"stealers": []})

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
        return _FakeResponse(12345)  # neither a list nor a dict

    with patch.object(paste_client, "get_by_service", return_value=_cfg()), \
         patch.object(paste_client, "get_http_client", _client_factory(get_impl)):
        result = paste_client.check_pastes("malformed-query@example.com")

    assert result is None


def test_check_pastes_returns_empty_list_when_stealers_key_is_wrong_type():
    def get_impl(url, **kwargs):
        return _FakeResponse({"stealers": "not-a-list"})

    with patch.object(paste_client, "get_by_service", return_value=_cfg()), \
         patch.object(paste_client, "get_http_client", _client_factory(get_impl)):
        result = paste_client.check_pastes("wrong-type-query@example.com")

    assert result is None
