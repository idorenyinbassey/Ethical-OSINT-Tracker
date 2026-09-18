"""app.services.darkweb_client — AHMIA.fi dark web search.

AHMIA's search form requires a per-page-load hidden anti-bot token to be
submitted alongside `q=`, or the request is redirected back to `/` with no
results. search_ahmia() now does a two-step fetch (load the form, extract
the token, then search) through the shared Tor/proxy-aware http client.
search_ahmia() is @cached(ttl=1800), so tests use a unique query per case
to avoid stale-cache collisions.
"""
import httpx
from unittest.mock import patch
from app.services import darkweb_client

_FORM_HTML = """
<html><body>
<form id="searchForm" class="autocomplete" action="/search/" method="get">
<input id="id_q" type="search" name="q" title="q">
<input type="hidden" name="5f0c8e" value="1a76fe">
<input type="submit" value="Search">
</form>
</body></html>
"""

_RESULTS_HTML = """
<ol class="searchResults">
<li class="result">
<h4><a href="/search/redirect_url=http://exampleonionabcdefghijklmnopqrstuvwxyz234567.onion/page">Example Title</a></h4>
<p>Example description text.</p>
<cite>exampleonionabcdefghijklmnopqrstuvwxyz234567.onion</cite>
</li>
<li class="result">
<h4><a href="/search/redirect_url=http://anotheronionabcdefghijklmnopqrstuvwxyz234567.onion/">Second Result</a></h4>
<p>Second description.</p>
<cite>anotheronionabcdefghijklmnopqrstuvwxyz234567.onion</cite>
</li>
</ol>
"""


class _FakeResponse:
    def __init__(self, text, status_code=200):
        self.text = text
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("error", request=None, response=self)


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


def test_search_ahmia_submits_extracted_hidden_token():
    fake_client = _FakeClient([
        _FakeResponse(_FORM_HTML),
        _FakeResponse(_RESULTS_HTML),
    ])

    with patch.object(darkweb_client, "get_http_client", _client_factory(fake_client)):
        result = darkweb_client.search_ahmia("token-query-1")

    search_call = fake_client.calls[1]
    assert search_call[1]["params"]["q"] == "token-query-1"
    assert search_call[1]["params"]["5f0c8e"] == "1a76fe"
    assert result["total"] == 2
    assert result["results"][0]["title"] == "Example Title"
    assert result["results"][0]["url"].endswith(".onion/page")
    assert result["results"][0]["description"] == "Example description text."


def test_search_ahmia_falls_back_when_token_fetch_fails():
    fake_client = _FakeClient([
        _FakeResponse("", status_code=500),
        _FakeResponse(_RESULTS_HTML),
    ])

    with patch.object(darkweb_client, "get_http_client", _client_factory(fake_client)):
        result = darkweb_client.search_ahmia("fallback-query-1")

    search_call = fake_client.calls[1]
    assert search_call[1]["params"] == {"q": "fallback-query-1"}
    assert result["total"] == 2


def test_search_ahmia_falls_back_when_form_has_no_hidden_field():
    fake_client = _FakeClient([
        _FakeResponse("<html><body><form id=\"searchForm\"></form></body></html>"),
        _FakeResponse(_RESULTS_HTML),
    ])

    with patch.object(darkweb_client, "get_http_client", _client_factory(fake_client)):
        result = darkweb_client.search_ahmia("no-hidden-field-1")

    search_call = fake_client.calls[1]
    assert search_call[1]["params"] == {"q": "no-hidden-field-1"}
    assert result["total"] == 2


def test_search_ahmia_returns_empty_results_list():
    fake_client = _FakeClient([
        _FakeResponse(_FORM_HTML),
        _FakeResponse("<ol class=\"searchResults\"></ol>"),
    ])

    with patch.object(darkweb_client, "get_http_client", _client_factory(fake_client)):
        result = darkweb_client.search_ahmia("zero-hits-1")

    assert result["results"] == []
    assert result["total"] == 0


def test_search_ahmia_handles_timeout():
    class _TimeoutClient:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def get(self, url, **kwargs):
            raise httpx.TimeoutException("timed out")

    with patch.object(darkweb_client, "get_http_client", _client_factory(_TimeoutClient())):
        result = darkweb_client.search_ahmia("timeout-query-1")

    assert result["error_type"] == "timeout"
    assert result["results"] == []


def test_search_ahmia_handles_http_error_on_search_request():
    fake_client = _FakeClient([
        _FakeResponse(_FORM_HTML),
        _FakeResponse("", status_code=503),
    ])

    with patch.object(darkweb_client, "get_http_client", _client_factory(fake_client)):
        result = darkweb_client.search_ahmia("http-error-query-1")

    assert result["error_type"] == "http_error"
    assert result["results"] == []


def test_extract_hidden_token_scopes_to_search_form_only():
    html = """
    <input type="hidden" name="outside" value="should-not-match">
    <form id="searchForm">
    <input type="hidden" name="inside" value="correct-token">
    </form>
    """
    assert darkweb_client._extract_hidden_token(html) == ("inside", "correct-token")


def test_extract_hidden_token_returns_none_when_no_form():
    assert darkweb_client._extract_hidden_token("<html><body>no form here</body></html>") is None
