"""app.services.imei_client — IMEI lookup. fetch_imei() now falls back
automatically to the free offline TAC database (app.services.tac_lookup)
whenever no paid IMEIService key is configured, or the paid provider
reports exhausted credits (402/403) — the fallback that fixes "once
credit is finished the freemium is over"."""
from types import SimpleNamespace
from unittest.mock import patch
from app.services import imei_client

VALID_IMEI = "863024073237518"  # TAC 86302407 exists in the bundled database


def _cfg(enabled=True, api_key=None, base_url="https://dash.imei.info/api"):
    return SimpleNamespace(is_enabled=enabled, api_key=api_key, base_url=base_url)


class _FakeResponse:
    def __init__(self, json_data=None, status_code=200):
        self._json = json_data
        self.status_code = status_code

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


def test_fetch_imei_rejects_bad_format():
    result = imei_client.fetch_imei("123")
    assert "error" in result


def test_fetch_imei_uses_offline_fallback_when_not_configured():
    with patch.object(imei_client, "get_by_service", return_value=None):
        result = imei_client.fetch_imei(VALID_IMEI)

    assert result["brand"] == "XIAOMI"
    assert "offline" in result["source"]


def test_fetch_imei_uses_offline_fallback_when_disabled():
    with patch.object(imei_client, "get_by_service", return_value=_cfg(enabled=False, api_key="k")):
        result = imei_client.fetch_imei(VALID_IMEI)

    assert result["brand"] == "XIAOMI"


def test_fetch_imei_uses_paid_provider_when_configured():
    def get_impl(url, **kwargs):
        assert "dash.imei.info" in url
        assert kwargs["headers"]["Authorization"] == "Bearer paid-key"
        return _FakeResponse({"brand": "Apple", "model": "iPhone 15"})

    with patch.object(imei_client, "get_by_service", return_value=_cfg(api_key="paid-key")), \
         patch.object(imei_client, "get_http_client", _client_factory(get_impl)):
        result = imei_client.fetch_imei(VALID_IMEI)

    assert result == {"brand": "Apple", "model": "iPhone 15"}


def test_fetch_imei_falls_back_to_offline_on_insufficient_balance():
    def get_impl(url, **kwargs):
        return _FakeResponse(status_code=402)

    with patch.object(imei_client, "get_by_service", return_value=_cfg(api_key="broke-key")), \
         patch.object(imei_client, "get_http_client", _client_factory(get_impl)):
        result = imei_client.fetch_imei(VALID_IMEI)

    assert result["brand"] == "XIAOMI"
    assert "offline" in result["source"]


def test_fetch_imei_falls_back_to_offline_on_forbidden():
    def get_impl(url, **kwargs):
        return _FakeResponse(status_code=403)

    with patch.object(imei_client, "get_by_service", return_value=_cfg(api_key="broke-key")), \
         patch.object(imei_client, "get_http_client", _client_factory(get_impl)):
        result = imei_client.fetch_imei(VALID_IMEI)

    assert result["brand"] == "XIAOMI"


def test_fetch_imei_returns_explicit_error_on_rejected_key():
    def get_impl(url, **kwargs):
        return _FakeResponse(status_code=401)

    with patch.object(imei_client, "get_by_service", return_value=_cfg(api_key="bad-key")), \
         patch.object(imei_client, "get_http_client", _client_factory(get_impl)):
        result = imei_client.fetch_imei(VALID_IMEI)

    assert result["error"] == "IMEI API key rejected (HTTP 401). Check your key in Settings."


def test_fetch_imei_falls_back_to_offline_on_connection_error():
    def get_impl(url, **kwargs):
        raise Exception("connection refused")

    with patch.object(imei_client, "get_by_service", return_value=_cfg(api_key="paid-key")), \
         patch.object(imei_client, "get_http_client", _client_factory(get_impl)):
        result = imei_client.fetch_imei(VALID_IMEI)

    assert result["brand"] == "XIAOMI"
