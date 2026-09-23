"""app.services.hunter_client — Hunter.io Email Verifier (existing),
Domain Search, and Email Finder. All three degrade to None (or, for
find_email, a {"found": False, ...} shape) when Hunter.io isn't
configured or a request fails, matching this codebase's established
graceful-degradation convention. hunter_client talks to Hunter.io via a
raw httpx.Client (not the shared get_http_client() proxy helper), so
tests patch httpx.Client directly within the module."""
from types import SimpleNamespace
from unittest.mock import patch
import httpx
from app.services import hunter_client


def _cfg(enabled=True, api_key="test-key", base_url=None):
    return SimpleNamespace(is_enabled=enabled, api_key=api_key, base_url=base_url)


class _FakeResponse:
    def __init__(self, json_data, status_code=200):
        self._json = json_data
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
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


def _patch_client(get_impl):
    return patch.object(hunter_client.httpx, "Client", lambda timeout=8: _FakeClient(get_impl))


# ── domain_search() ─────────────────────────────────────────────────────────

def test_domain_search_returns_none_when_not_configured():
    with patch.object(hunter_client, "get_by_service", return_value=None):
        assert hunter_client.domain_search("example.com") is None


def test_domain_search_returns_none_when_enabled_but_no_key():
    with patch.object(hunter_client, "get_by_service", return_value=_cfg(api_key=None)):
        assert hunter_client.domain_search("example.com") is None


def test_domain_search_maps_response_fields():
    def get_impl(url, **kwargs):
        assert "domain-search" in url
        assert kwargs["params"]["domain"] == "example.com"
        assert kwargs["params"]["api_key"] == "test-key"
        return _FakeResponse({"data": {
            "organization": "Example Inc",
            "pattern": "{first}.{last}@example.com",
            "emails": [
                {"value": "jane.doe@example.com", "first_name": "Jane", "last_name": "Doe",
                 "position": "Engineer", "confidence": 90},
            ],
        }})

    with patch.object(hunter_client, "get_by_service", return_value=_cfg()), _patch_client(get_impl):
        result = hunter_client.domain_search("example.com")

    assert result["organization"] == "Example Inc"
    assert result["pattern"] == "{first}.{last}@example.com"
    assert result["total_emails"] == 1
    assert result["emails"][0]["email"] == "jane.doe@example.com"
    assert result["emails"][0]["confidence"] == 90


def test_domain_search_caps_at_twenty_emails():
    entries = [{"value": f"user{i}@example.com"} for i in range(30)]

    def get_impl(url, **kwargs):
        return _FakeResponse({"data": {"emails": entries}})

    with patch.object(hunter_client, "get_by_service", return_value=_cfg()), _patch_client(get_impl):
        result = hunter_client.domain_search("cap-example.com")

    assert result["total_emails"] == 20


def test_domain_search_skips_malformed_entries():
    def get_impl(url, **kwargs):
        return _FakeResponse({"data": {"emails": [{"value": ""}, "not-a-dict", {"value": "ok@example.com"}]}})

    with patch.object(hunter_client, "get_by_service", return_value=_cfg()), _patch_client(get_impl):
        result = hunter_client.domain_search("malformed-example.com")

    assert result["total_emails"] == 1
    assert result["emails"][0]["email"] == "ok@example.com"


def test_domain_search_returns_none_on_http_error():
    def get_impl(url, **kwargs):
        return _FakeResponse({}, status_code=500)

    with patch.object(hunter_client, "get_by_service", return_value=_cfg()), _patch_client(get_impl):
        assert hunter_client.domain_search("error-example.com") is None


def test_domain_search_returns_none_on_timeout():
    def get_impl(url, **kwargs):
        raise httpx.TimeoutException("timed out")

    with patch.object(hunter_client, "get_by_service", return_value=_cfg()), _patch_client(get_impl):
        assert hunter_client.domain_search("timeout-example.com") is None


# ── find_email() ─────────────────────────────────────────────────────────────

def test_find_email_returns_none_when_not_configured():
    with patch.object(hunter_client, "get_by_service", return_value=None):
        assert hunter_client.find_email("example.com", "Jane", "Doe") is None


def test_find_email_returns_found_true_on_match():
    def get_impl(url, **kwargs):
        assert "email-finder" in url
        assert kwargs["params"]["first_name"] == "Jane"
        assert kwargs["params"]["last_name"] == "Doe"
        return _FakeResponse({"data": {"email": "jane.doe@example.com", "score": 95, "position": "Engineer"}})

    with patch.object(hunter_client, "get_by_service", return_value=_cfg()), _patch_client(get_impl):
        result = hunter_client.find_email("match-example.com", "Jane", "Doe")

    assert result == {"found": True, "email": "jane.doe@example.com", "score": 95, "position": "Engineer"}


def test_find_email_returns_found_false_on_no_match():
    def get_impl(url, **kwargs):
        return _FakeResponse({"data": {}})

    with patch.object(hunter_client, "get_by_service", return_value=_cfg()), _patch_client(get_impl):
        result = hunter_client.find_email("no-match-example.com", "Nobody", "Real")

    assert result == {"found": False, "error": None}


def test_find_email_returns_found_false_on_http_error():
    def get_impl(url, **kwargs):
        return _FakeResponse({}, status_code=403)

    with patch.object(hunter_client, "get_by_service", return_value=_cfg()), _patch_client(get_impl):
        result = hunter_client.find_email("http-error-example.com", "Jane", "Doe")

    assert result["found"] is False
    assert "403" in result["error"]


def test_find_email_returns_found_false_on_timeout():
    def get_impl(url, **kwargs):
        raise httpx.TimeoutException("timed out")

    with patch.object(hunter_client, "get_by_service", return_value=_cfg()), _patch_client(get_impl):
        result = hunter_client.find_email("timeout-example.com", "Jane", "Doe")

    assert result["found"] is False
