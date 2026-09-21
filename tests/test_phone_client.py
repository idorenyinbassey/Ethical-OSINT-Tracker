"""app.services.phone_client — Phone Lookup's free, offline baseline
(via the `phonenumbers` library) plus optional NumVerify enrichment and a
passive DuckDuckGo web-mention search.

Previously Phone Lookup was entirely dead without a paid NumVerify key;
lookup_phone() now always returns real data via phonenumbers, with
NumVerify layered on top field-by-field only where configured and
non-empty. search_phone_mentions()/numverify_client.validate_phone() are
both @cached(ttl=3600), so tests use a unique phone number per case to
avoid stale-cache collisions, matching the convention already used in
tests/test_hibp_client.py.
"""
from types import SimpleNamespace
from unittest.mock import patch

from tests.conftest import login
from app.services import phone_client


# ── enrich_offline() ─────────────────────────────────────────────────────────

def test_enrich_offline_valid_us_mobile_or_fixed_line():
    result = phone_client.enrich_offline("+14155552671")
    assert result["valid"] is True
    assert result["possible"] is True
    assert result["country_code"] == "US"
    assert result["country_name"] == "United States"
    assert result["e164"] == "+14155552671"
    assert result["source"] == "offline (phonenumbers)"
    assert "error" not in result


def test_enrich_offline_uk_landline_is_fixed_line():
    result = phone_client.enrich_offline("+442071838750")
    assert result["valid"] is True
    assert result["line_type"] == "Fixed Line"
    assert result["location"]  # area-code-level region is available for UK landlines


def test_enrich_offline_unparseable_input_returns_error():
    result = phone_client.enrich_offline("not-a-phone-number")
    assert result["valid"] is False
    assert "error" in result


def test_enrich_offline_impossible_number_is_invalid_but_not_an_error():
    # A parseable-shaped but impossible number should report valid=False
    # via the library's own validation, not raise or short-circuit as a
    # parse error (those are distinct failure modes).
    result = phone_client.enrich_offline("+1000")
    assert result["valid"] is False


# ── search_phone_mentions() ──────────────────────────────────────────────────

class _FakeResponse:
    def __init__(self, text, status_code=200):
        self.text = text
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            import httpx
            raise httpx.HTTPStatusError("error", request=None, response=self)


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


_SAMPLE_DDG_HTML = """
<div class="results">
  <div class="result">
    <a rel="nofollow" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fforum%2Fpost123&amp;rut=abc" class="result__a">Someone posted their number on a forum</a>
    <a class="result__snippet" href="//duckduckgo.com/l/?uddg=x">Forum thread mentioning <b>this number</b> as a contact.</a>
  </div>
</div>
"""


def test_search_phone_mentions_parses_results_and_resolves_ddg_redirect():
    def get_impl(url, **kwargs):
        assert "html.duckduckgo.com" in url
        return _FakeResponse(_SAMPLE_DDG_HTML)

    with patch.object(phone_client, "get_http_client", _client_factory(get_impl)):
        result = phone_client.search_phone_mentions("unique-mention-query-1")

    assert result["status"] == "ok"
    assert result["total"] == 1
    assert result["results"][0]["title"] == "Someone posted their number on a forum"
    assert result["results"][0]["url"] == "https://example.com/forum/post123"
    assert "this number" in result["results"][0]["snippet"]


def test_search_phone_mentions_no_matches_returns_empty():
    with patch.object(phone_client, "get_http_client", _client_factory(lambda url, **kw: _FakeResponse("<html></html>"))):
        result = phone_client.search_phone_mentions("unique-mention-query-2")

    assert result == {"status": "ok", "results": [], "total": 0}


def test_search_phone_mentions_returns_error_status_on_request_failure():
    def get_impl(url, **kwargs):
        raise ConnectionError("network down")

    with patch.object(phone_client, "get_http_client", _client_factory(get_impl)):
        result = phone_client.search_phone_mentions("unique-mention-query-3")

    assert result["status"] == "error"
    assert result["results"] == []


# ── lookup_phone() ───────────────────────────────────────────────────────────

def test_lookup_phone_returns_error_for_unparseable_input_without_any_network_call():
    with patch.object(phone_client, "search_phone_mentions") as mock_mentions, \
         patch.object(phone_client.numverify_client, "validate_phone") as mock_numverify:
        result = phone_client.lookup_phone("definitely not a phone number")

    assert result["valid"] is False
    assert "error" in result
    mock_mentions.assert_not_called()
    mock_numverify.assert_not_called()


def test_lookup_phone_works_with_no_numverify_configured():
    with patch.object(phone_client.numverify_client, "validate_phone", return_value=None), \
         patch.object(phone_client, "search_phone_mentions", return_value={"status": "ok", "results": [], "total": 0}):
        result = phone_client.lookup_phone("+14155552672")

    assert result["valid"] is True
    assert result["source"] == "offline (phonenumbers)"
    assert result["country_name"] == "United States"
    assert result["web_mentions"] == {"status": "ok", "results": [], "total": 0}


def test_lookup_phone_merges_numverify_fields_over_offline_when_non_empty():
    numverify_result = {
        "valid": True, "country_code": "US", "country_name": "United States",
        "carrier": "Verizon Wireless", "line_type": "mobile", "location": "California",
    }
    with patch.object(phone_client.numverify_client, "validate_phone", return_value=numverify_result), \
         patch.object(phone_client, "search_phone_mentions", return_value={"status": "ok", "results": [], "total": 0}):
        result = phone_client.lookup_phone("+14155552673")

    assert result["carrier"] == "Verizon Wireless"
    assert result["line_type"] == "mobile"
    assert result["location"] == "California"
    assert result["source"] == "NumVerify + offline enrichment"
    # Fields NumVerify never provides at all stay from the offline pass.
    assert result["e164"] == "+14155552673"


def test_lookup_phone_keeps_offline_value_when_numverify_field_is_blank():
    # A paid provider's own blank/empty field must never blank out a
    # value the free offline library already filled in.
    numverify_result = {"valid": True, "country_code": "US", "country_name": "United States",
                         "carrier": "", "line_type": "", "location": ""}
    with patch.object(phone_client.numverify_client, "validate_phone", return_value=numverify_result), \
         patch.object(phone_client, "enrich_offline", return_value={
             "valid": True, "possible": True, "country_code": "US", "country_name": "United States",
             "carrier": "Offline Carrier Guess", "line_type": "Mobile", "location": "San Francisco, CA",
             "e164": "+14155552674", "national_format": "(415) 555-2674",
             "international_format": "+1 415-555-2674", "source": "offline (phonenumbers)",
         }), \
         patch.object(phone_client, "search_phone_mentions", return_value={"status": "ok", "results": [], "total": 0}):
        result = phone_client.lookup_phone("+14155552674")

    assert result["carrier"] == "Offline Carrier Guess"
    assert result["line_type"] == "Mobile"
    assert result["location"] == "San Francisco, CA"


# ── /investigate/phone route ─────────────────────────────────────────────────

def test_phone_route_returns_offline_data_with_no_numverify_configured(app, client, user_a, case_of_a):
    login(client, user_a.username)
    with patch("app.services.phone_client.numverify_client.validate_phone", return_value=None), \
         patch("app.services.phone_client.search_phone_mentions", return_value={"status": "ok", "results": [], "total": 0}):
        resp = client.post("/investigate/phone", data={
            "query": "+14155552675", "case_id": str(case_of_a.id),
        })
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "United States" in body
    assert "offline (phonenumbers)" in body


def test_phone_route_shows_error_for_unparseable_input(app, client, user_a, case_of_a):
    login(client, user_a.username)
    resp = client.post("/investigate/phone", data={
        "query": "definitely-not-a-number", "case_id": str(case_of_a.id),
    })
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "does not look like a valid phone number" in body

