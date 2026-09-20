"""app.services.company_client — registry-by-registry unit tests.

Covers the CAC Nigeria switch to the richer postapp.cac.gov.ng endpoint,
the four manual-referral-only additions (Singapore, Estonia, Ireland,
Brazil — no confirmed stable name-search API, so they degrade to a
"search manually" link rather than guessing an endpoint), and the two
optional-key additions (Australia ABN Lookup, New Zealand NZBN), which
mirror UK Companies House's existing api_key-gated shape. None of these
endpoints can be exercised against the real network from this app's
development sandbox, so every test mocks get_http_client, matching the
convention already established in tests/test_darkweb_client.py.
"""
import httpx
from unittest.mock import patch

from app.services import company_client


class _FakeResponse:
    def __init__(self, payload=None, text="", status_code=200):
        self._payload = payload
        self.text = text
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
        self.calls.append(("GET", url, kwargs))
        return self._responses.pop(0)

    def post(self, url, **kwargs):
        self.calls.append(("POST", url, kwargs))
        return self._responses.pop(0)


def _client_factory(fake_client):
    def factory(timeout=8):
        return fake_client
    return factory


# ── CAC Nigeria (switched to postapp.cac.gov.ng) ────────────────────────────

def test_nigeria_cac_posts_new_endpoint_and_maps_fields():
    payload = {
        "success": True,
        "data": [{
            "approvedName": "Acme Nigeria Ltd", "rcNumber": "RC123456",
            "active": True, "companyTypeName": "Private Company",
            "address": "1 Lagos Street", "city": "Lagos", "state": "Lagos",
            "email": "info@acme.ng",
        }],
    }
    fake_client = _FakeClient([_FakeResponse(payload)])
    with patch.object(company_client, "get_http_client", _client_factory(fake_client)):
        result = company_client._search_nigeria_cac("Acme")

    method, url, kwargs = fake_client.calls[0]
    assert method == "POST"
    assert url == "https://postapp.cac.gov.ng/postapp/api/front-office/search/company-business-name-it"
    assert kwargs["json"] == {"searchTerm": "Acme"}

    assert result["error"] is None
    assert result["found"] == [{
        "name": "Acme Nigeria Ltd", "rc_number": "RC123456", "status": "Active",
        "type": "Private Company", "address": "1 Lagos Street", "city": "Lagos",
        "state": "Lagos", "email": "info@acme.ng",
    }]


def test_nigeria_cac_falls_back_on_malformed_response():
    fake_client = _FakeClient([_FakeResponse({"success": False})])
    with patch.object(company_client, "get_http_client", _client_factory(fake_client)):
        result = company_client._search_nigeria_cac("Acme")

    assert result["found"] == []
    assert result["error"] is None
    assert result["note"]
    assert result["manual_url"]


def test_nigeria_cac_falls_back_gracefully_on_network_failure():
    class _RaisingClient:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def post(self, *a, **k):
            raise httpx.ConnectError("boom")

    with patch.object(company_client, "get_http_client", lambda timeout=8: _RaisingClient()):
        result = company_client._search_nigeria_cac("Acme")

    assert result["found"] == []
    assert result["error"] is None
    assert result["manual_url"]


# ── Manual-referral-only registries ─────────────────────────────────────────

def test_manual_referral_only_registries_return_no_results_and_a_link():
    for fn in (
        company_client._search_singapore_acra,
        company_client._search_estonia_business_register,
        company_client._search_ireland_cro,
        company_client._search_brazil_cnpj,
    ):
        result = fn("Acme")
        assert result["found"] == []
        assert result["error"] is None
        assert result["note"]
        assert result["manual_url"].startswith("https://")


# ── Australia ABN Lookup ────────────────────────────────────────────────────

def test_australia_abn_without_key_is_manual_referral():
    result = company_client._search_australia_abn("Acme", None)
    assert result["found"] == []
    assert result["manual_url"]
    assert "guid" in result["note"].lower() or "GUID" in result["note"]


def test_australia_abn_with_key_maps_matching_names():
    payload = {"Names": [{"Name": "Acme Pty Ltd", "Abn": "51824753556",
                          "AbnStatus": "Active", "NameType": "MN"}]}
    import json as _json
    fake_client = _FakeClient([_FakeResponse(text=_json.dumps(payload))])
    with patch.object(company_client, "get_http_client", _client_factory(fake_client)):
        result = company_client._search_australia_abn("Acme", "test-guid")

    method, url, kwargs = fake_client.calls[0]
    assert kwargs["params"]["guid"] == "test-guid"
    assert result["found"] == [{
        "name": "Acme Pty Ltd", "abn": "51824753556", "status": "Active", "type": "MN",
    }]


def test_australia_abn_falls_back_on_bad_response():
    fake_client = _FakeClient([_FakeResponse(text="not json")])
    with patch.object(company_client, "get_http_client", _client_factory(fake_client)):
        result = company_client._search_australia_abn("Acme", "test-guid")

    assert result["found"] == []
    assert result["error"] is None
    assert result["manual_url"]


# ── New Zealand NZBN ─────────────────────────────────────────────────────────

def test_new_zealand_without_key_is_manual_referral():
    result = company_client._search_new_zealand_nzbn("Acme", None)
    assert result["found"] == []
    assert result["manual_url"]


def test_new_zealand_with_key_maps_entities_and_sends_subscription_header():
    payload = {"items": [{"entityName": "Acme NZ Ltd", "nzbn": "9429000000000",
                          "entityStatusDescription": "Registered", "entityTypeDescription": "LTD"}]}
    fake_client = _FakeClient([_FakeResponse(payload)])
    with patch.object(company_client, "get_http_client", _client_factory(fake_client)):
        result = company_client._search_new_zealand_nzbn("Acme", "test-key")

    method, url, kwargs = fake_client.calls[0]
    assert kwargs["headers"]["Ocp-Apim-Subscription-Key"] == "test-key"
    assert result["found"] == [{
        "name": "Acme NZ Ltd", "nzbn": "9429000000000", "status": "Registered", "type": "LTD",
    }]


def test_new_zealand_falls_back_on_network_failure():
    class _RaisingClient:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def get(self, *a, **k):
            raise httpx.ConnectError("boom")

    with patch.object(company_client, "get_http_client", lambda timeout=8: _RaisingClient()):
        result = company_client._search_new_zealand_nzbn("Acme", "test-key")

    assert result["found"] == []
    assert result["manual_url"]


# ── search_companies() wiring ────────────────────────────────────────────────

def test_search_companies_includes_all_eleven_registries_in_order():
    class _RaisingClient:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def get(self, *a, **k):
            raise httpx.ConnectError("no network in tests")

        def post(self, *a, **k):
            raise httpx.ConnectError("no network in tests")

    with patch.object(company_client, "get_http_client", lambda timeout=8: _RaisingClient()):
        result = company_client.search_companies("Acme")

    assert list(result["results"].keys()) == [
        "us_edgar", "uk", "nigeria", "canada", "cyprus", "singapore",
        "estonia", "ireland", "brazil", "australia", "new_zealand",
        "duckduckgo", "google_dorks",
    ]
