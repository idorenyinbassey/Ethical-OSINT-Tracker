"""app.services.hibp_client — email breach checking. HIBP's real API has
had no free tier since 2024, so check_breaches() now falls back
automatically to XposedOrNot's free, keyless API whenever no paid HIBP
key is configured, while still using real HIBP (richer per-breach
detail) when a key is present. check_breaches() is @cached(ttl=3600), so
tests use a unique email per case to avoid stale-cache collisions."""
from types import SimpleNamespace
from unittest.mock import patch
from app.services import hibp_client


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


# ── Provider selection ──────────────────────────────────────────────────────

def test_check_breaches_uses_xposedornot_when_no_config_row():
    def get_impl(url, **kwargs):
        assert "api.xposedornot.com" in url
        return _FakeResponse({"breaches": [], "email": "x", "status": "success"})

    with patch.object(hibp_client, "get_by_service", return_value=None), \
         patch.object(hibp_client, "get_http_client", _client_factory(get_impl)):
        result = hibp_client.check_breaches("no-config-row-1@example.com")

    assert result == []


def test_check_breaches_uses_xposedornot_when_enabled_but_no_key():
    def get_impl(url, **kwargs):
        assert "api.xposedornot.com" in url
        return _FakeResponse({"breaches": [], "email": "x", "status": "success"})

    with patch.object(hibp_client, "get_by_service", return_value=_cfg(enabled=True, api_key=None)), \
         patch.object(hibp_client, "get_http_client", _client_factory(get_impl)):
        result = hibp_client.check_breaches("no-key-1@example.com")

    assert result == []


def test_check_breaches_returns_none_when_explicitly_disabled():
    with patch.object(hibp_client, "get_by_service", return_value=_cfg(enabled=False, api_key="somekey")):
        assert hibp_client.check_breaches("disabled-1@example.com") is None


def test_check_breaches_uses_real_hibp_when_key_configured():
    captured = {}

    def get_impl(url, **kwargs):
        captured["url"] = url
        captured["headers"] = kwargs.get("headers")
        return _FakeResponse([{"Name": "Adobe", "BreachDate": "2013-10-04",
                                "DataClasses": ["Emails", "Passwords"], "Description": "desc"}])

    with patch.object(hibp_client, "get_by_service", return_value=_cfg(api_key="paid-key-123")), \
         patch.object(hibp_client, "get_http_client", _client_factory(get_impl)):
        result = hibp_client.check_breaches("hibp-key-query-1@example.com")

    assert "haveibeenpwned.com" in captured["url"]
    assert captured["headers"]["hibp-api-key"] == "paid-key-123"
    assert result == [{"name": "Adobe", "date": "2013-10-04",
                        "data_classes": ["Emails", "Passwords"], "description": "desc"}]


# ── XposedOrNot parsing ──────────────────────────────────────────────────────

def test_xposedornot_returns_empty_list_on_404():
    def get_impl(url, **kwargs):
        return _FakeResponse({}, status_code=404)

    with patch.object(hibp_client, "get_by_service", return_value=None), \
         patch.object(hibp_client, "get_http_client", _client_factory(get_impl)):
        result = hibp_client.check_breaches("zero-hits-xon-1@example.com")

    assert result == []


def test_xposedornot_parses_nested_breach_list():
    def get_impl(url, **kwargs):
        return _FakeResponse({"breaches": [["Adobe", "LinkedIn"]], "email": "x", "status": "success"})

    with patch.object(hibp_client, "get_by_service", return_value=None), \
         patch.object(hibp_client, "get_http_client", _client_factory(get_impl)):
        result = hibp_client.check_breaches("nested-hits-1@example.com")

    names = [b["name"] for b in result]
    assert names == ["Adobe", "LinkedIn"]
    assert all(b["date"] == "" and b["data_classes"] == [] and b["description"] == "" for b in result)


def test_xposedornot_tolerates_flat_breach_list():
    def get_impl(url, **kwargs):
        return _FakeResponse({"breaches": ["Adobe", "LinkedIn"]})

    with patch.object(hibp_client, "get_by_service", return_value=None), \
         patch.object(hibp_client, "get_http_client", _client_factory(get_impl)):
        result = hibp_client.check_breaches("flat-hits-1@example.com")

    names = [b["name"] for b in result]
    assert names == ["Adobe", "LinkedIn"]


def test_xposedornot_returns_none_on_malformed_response():
    def get_impl(url, **kwargs):
        return _FakeResponse(["not", "a", "dict"])

    with patch.object(hibp_client, "get_by_service", return_value=None), \
         patch.object(hibp_client, "get_http_client", _client_factory(get_impl)):
        result = hibp_client.check_breaches("malformed-1@example.com")

    assert result is None


def test_xposedornot_returns_none_on_http_error():
    def get_impl(url, **kwargs):
        return _FakeResponse({}, status_code=500)

    with patch.object(hibp_client, "get_by_service", return_value=None), \
         patch.object(hibp_client, "get_http_client", _client_factory(get_impl)):
        result = hibp_client.check_breaches("error-1@example.com")

    assert result is None


def test_xposedornot_returns_none_on_timeout():
    def get_impl(url, **kwargs):
        raise Exception("timed out")

    with patch.object(hibp_client, "get_by_service", return_value=None), \
         patch.object(hibp_client, "get_http_client", _client_factory(get_impl)):
        result = hibp_client.check_breaches("timeout-1@example.com")

    assert result is None


# ── check_password_pwned (unaffected, still keyless) ──────────────────────────

def test_check_password_pwned_uses_k_anonymity_range():
    def get_impl(url, **kwargs):
        assert "pwnedpasswords.com/range/" in url
        return SimpleNamespace(status_code=200, text="1E4C9B93F3F0682250B6CF8331B7EE68FD8:5\nOTHER:1")

    with patch.object(hibp_client, "get_http_client", _client_factory(get_impl)):
        # SHA1("password") = 5BAA61E4C9B93F3F0682250B6CF8331B7EE68FD, suffix matches the fixture above
        count = hibp_client.check_password_pwned("password")

    assert count == 5
