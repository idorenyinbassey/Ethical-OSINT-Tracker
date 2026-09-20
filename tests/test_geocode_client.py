"""app.services.geocode_client — forward geocoding via Nominatim, for
plotting a "suspected" location on the map from a free-text address
(currently: Company Registry hits with no lat/lon of their own).
Always checks app.repositories.geocode_cache_repository first; a live
lookup (found or not) is written back so the exact same address is
never geocoded twice, per Nominatim's usage policy."""
import httpx
from unittest.mock import patch

from app.services import geocode_client


class _FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("error", request=None, response=self)

    def json(self):
        return self._payload


class _FakeClient:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self._responses.pop(0)


def _client_factory(fake_client):
    def factory(timeout=8):
        return fake_client
    return factory


def _no_sleep():
    return patch.object(geocode_client.time, "sleep", lambda s: None)


def test_geocode_returns_coordinates_on_a_match(app):
    fake_client = _FakeClient([
        _FakeResponse([{"lat": "51.5074", "lon": "-0.1278", "display_name": "London, UK"}]),
    ])
    with app.app_context(), _no_sleep(), patch.object(geocode_client, "get_http_client", _client_factory(fake_client)):
        result = geocode_client.geocode("10 Downing Street, London")

    assert result == {"lat": 51.5074, "lon": -0.1278, "display_name": "London, UK"}
    call_url, call_kwargs = fake_client.calls[0]
    assert call_url == "https://nominatim.openstreetmap.org/search"
    assert call_kwargs["params"]["q"] == "10 Downing Street, London"
    assert "User-Agent" in call_kwargs["headers"]


def test_geocode_returns_none_when_nominatim_finds_nothing(app):
    fake_client = _FakeClient([_FakeResponse([])])
    with app.app_context(), _no_sleep(), patch.object(geocode_client, "get_http_client", _client_factory(fake_client)):
        result = geocode_client.geocode("not a real address at all xyz123")
    assert result is None


def test_geocode_returns_none_on_blank_input(app):
    with app.app_context():
        assert geocode_client.geocode("   ") is None
        assert geocode_client.geocode("") is None


def test_geocode_caches_a_successful_lookup_and_skips_the_network_next_time(app):
    fake_client = _FakeClient([
        _FakeResponse([{"lat": "1.0", "lon": "2.0", "display_name": "Somewhere"}]),
    ])
    with app.app_context(), _no_sleep(), patch.object(geocode_client, "get_http_client", _client_factory(fake_client)):
        first = geocode_client.geocode("123 Example St")
        second = geocode_client.geocode("123 Example St")

    assert first == second == {"lat": 1.0, "lon": 2.0, "display_name": "Somewhere"}
    assert len(fake_client.calls) == 1


def test_geocode_caches_a_miss_too_and_skips_the_network_next_time(app):
    fake_client = _FakeClient([_FakeResponse([])])
    with app.app_context(), _no_sleep(), patch.object(geocode_client, "get_http_client", _client_factory(fake_client)):
        first = geocode_client.geocode("nowhere at all 987")
        second = geocode_client.geocode("nowhere at all 987")

    assert first is None
    assert second is None
    assert len(fake_client.calls) == 1


def test_geocode_handles_network_failure_gracefully(app):
    class _RaisingClient:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def get(self, *a, **k):
            raise httpx.ConnectError("boom")

    with app.app_context(), _no_sleep(), patch.object(geocode_client, "get_http_client", lambda timeout=8: _RaisingClient()):
        assert geocode_client.geocode("some address") is None
