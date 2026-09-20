"""app.services.social_client._extract_contact_info — best-effort scraping
of contact-relevant signals (emails, rel="me" cross-linked profiles) from
an already-fetched, confirmed-found profile page. Deliberately narrow in
scope: emails only come from mailto: links and the OG/Twitter bio text
(never raw HTML, to avoid tracking-script noise), and cross-links only
come from the high-confidence rel="me" convention, not arbitrary URLs."""
from unittest.mock import patch
from app.services import social_client
from app.services.social_client import _extract_contact_info, _check_site


def test_extracts_mailto_link():
    html = '<html><body><a href="mailto:john@example.com">Email me</a></body></html>'
    result = _extract_contact_info(html)
    assert result["emails"] == ["john@example.com"]


def test_extracts_email_from_bio_text_not_html():
    html = '<html><body><script>var fake = "noise@tracker.internal";</script></body></html>'
    result = _extract_contact_info(html, bio="Contact me at jane@example.com for work.")
    assert result["emails"] == ["jane@example.com"]
    assert "noise@tracker.internal" not in result.get("emails", [])


def test_does_not_scan_raw_html_for_emails_without_bio():
    # An email-shaped string sitting in a <script> tag (common analytics/
    # tracking noise) must never be picked up — only mailto: links and the
    # bio text are trusted sources.
    html = '<html><body><script>ping("noise@tracker.internal");</script></body></html>'
    result = _extract_contact_info(html)
    assert "emails" not in result


def test_dedupes_and_caps_emails_at_three():
    html = "".join(f'<a href="mailto:user{i}@example.com">c</a>' for i in range(5))
    html += '<a href="mailto:user0@example.com">dup</a>'
    result = _extract_contact_info(html)
    assert len(result["emails"]) == 3
    assert result["emails"][0] == "user0@example.com"


def test_extracts_rel_me_linked_domain():
    html = '<html><body><a rel="me" href="https://mastodon.social/@johndoe">Mastodon</a></body></html>'
    result = _extract_contact_info(html)
    assert result["linked_domains"] == ["mastodon.social"]


def test_ignores_links_without_rel_me():
    html = '<html><body><a href="https://spammy-ad-network.example/x">Ad</a></body></html>'
    result = _extract_contact_info(html)
    assert "linked_domains" not in result


def test_rel_me_handles_multi_value_rel_attribute():
    html = '<html><body><a rel="nofollow me" href="https://example.org/johndoe">Site</a></body></html>'
    result = _extract_contact_info(html)
    assert result["linked_domains"] == ["example.org"]


def test_returns_empty_dict_for_page_with_no_signals():
    html = "<html><body><p>Just a normal profile page.</p></body></html>"
    result = _extract_contact_info(html)
    assert result == {}


def test_never_raises_on_malformed_html():
    result = _extract_contact_info("<html><a href='mailto:broken")
    assert isinstance(result, dict)


def test_decodes_percent_encoded_mailto_address():
    html = '<html><body><a href="mailto:john%2Edoe%40example.com">Email</a></body></html>'
    result = _extract_contact_info(html)
    assert result["emails"] == ["john.doe@example.com"]


def test_bio_email_excludes_trailing_sentence_period():
    result = _extract_contact_info("<html></html>", bio="Contact alice@example.com.")
    assert result["emails"] == ["alice@example.com"]


def test_bio_email_handles_multi_level_domain():
    result = _extract_contact_info("<html></html>", bio="Reach me at bob@mail.example.co.uk today.")
    assert result["emails"] == ["bob@mail.example.co.uk"]


def test_rel_me_uses_hostname_not_netloc_strips_port():
    html = '<html><body><a rel="me" href="https://example.com:8443/profile">Site</a></body></html>'
    result = _extract_contact_info(html)
    assert result["linked_domains"] == ["example.com"]


def test_rel_me_rejects_url_with_userinfo():
    html = '<html><body><a rel="me" href="https://user:password@example.com/profile">Site</a></body></html>'
    result = _extract_contact_info(html)
    assert "linked_domains" not in result


def test_rel_me_rejects_non_http_scheme():
    html = '<html><body><a rel="me" href="mailto:someone@example.com">Site</a></body></html>'
    result = _extract_contact_info(html)
    assert "linked_domains" not in result


# ── _check_site: contact extraction gated on confidence ─────────────────────

class _FakeResponse:
    def __init__(self, text, status_code=200, url="https://example.test/somepage"):
        self.text = text
        self.status_code = status_code
        self.url = url


class _FakeClient:
    def __init__(self, response):
        self._response = response

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def get(self, url, **kwargs):
        return self._response


def _client_factory(response):
    def factory(timeout=10):
        return _FakeClient(response)
    return factory


_HTML_WITH_CONTACT = '<html><body><a href="mailto:john@example.com">Email</a></body></html>'


def test_check_site_skips_contact_extraction_on_low_confidence():
    # final URL doesn't contain the username -> "low" confidence per the
    # status_code branch's own logic.
    response = _FakeResponse(_HTML_WITH_CONTACT, url="https://example.test/generic-landing-page")
    defn = {"url": "https://example.test/{username}", "error_type": "status_code", "error_code": 404}
    with patch.object(social_client, "get_http_client", _client_factory(response)):
        result = _check_site("Example", defn, "johndoe")

    assert result["found"] is True
    assert result["confidence"] == "low"
    assert "emails" not in result


def test_check_site_extracts_contact_on_high_confidence():
    response = _FakeResponse(_HTML_WITH_CONTACT, url="https://example.test/johndoe")
    defn = {"url": "https://example.test/{username}", "error_type": "status_code", "error_code": 404}
    with patch.object(social_client, "get_http_client", _client_factory(response)):
        result = _check_site("Example", defn, "johndoe")

    assert result["found"] is True
    assert result["confidence"] == "high"
    assert result["emails"] == ["john@example.com"]


# ── Sherlock conversion: headers + regexCheck now carried over ──────────────
# Confirmed by diffing app/data/sherlock_sites.json's real LinkedIn/
# Instagram/TikTok/Snapchat/Pinterest/Twitter entries against our own
# long-frozen local ones: Sherlock uses a realistic browser UA + a
# username-shape regexCheck for LinkedIn, a read-only mirror (imginn.com)
# to probe Instagram instead of instagram.com directly, and an oEmbed API
# probe for Pinterest — all meaningfully better anti-bot techniques that
# an earlier version of this conversion silently dropped.

def test_sherlock_to_defn_carries_over_headers_and_regex_check():
    entry = {
        "url": "https://linkedin.com/in/{}",
        "errorType": "status_code",
        "headers": {"User-Agent": "Mozilla/5.0 Chrome/120.0"},
        "regexCheck": "^[a-zA-Z0-9]{3,100}$",
    }
    defn = social_client._sherlock_to_defn(entry)
    assert defn["headers"] == {"User-Agent": "Mozilla/5.0 Chrome/120.0"}
    assert defn["regex_check"] == "^[a-zA-Z0-9]{3,100}$"


def test_sherlock_to_defn_omits_headers_and_regex_check_when_absent():
    entry = {"url": "https://example.com/{}", "errorType": "status_code"}
    defn = social_client._sherlock_to_defn(entry)
    assert "headers" not in defn
    assert "regex_check" not in defn


def test_get_all_sites_prefers_sherlocks_definition_for_bot_walled_platforms():
    fake_sherlock = {
        "LinkedIn": {
            "url": "https://linkedin.com/in/{}", "errorType": "status_code",
            "headers": {"User-Agent": "Chrome/120.0"}, "regexCheck": "^[a-zA-Z0-9]{3,100}$",
        },
        "Instagram": {"url": "https://instagram.com/{}", "urlProbe": "https://imginn.com/{}", "errorType": "status_code"},
    }
    with patch.object(social_client, "_load_sherlock_sites", return_value=fake_sherlock):
        merged = social_client._get_all_sites()

    # Our own local LinkedIn/Instagram entries (no headers/url_probe) must
    # have been replaced by Sherlock's, not merely supplemented.
    assert merged["LinkedIn"]["headers"] == {"User-Agent": "Chrome/120.0"}
    assert merged["LinkedIn"]["regex_check"] == "^[a-zA-Z0-9]{3,100}$"
    assert merged["Instagram"]["url_probe"] == "https://imginn.com/{username}"


def test_get_all_sites_leaves_non_preferred_overlaps_untouched():
    # GitHub isn't in _PREFER_SHERLOCK — our own (identical, here
    # deliberately different to prove it) local definition must win.
    fake_sherlock = {"GitHub": {"url": "https://sherlock-would-use-this.example/{}", "errorType": "status_code"}}
    with patch.object(social_client, "_load_sherlock_sites", return_value=fake_sherlock):
        merged = social_client._get_all_sites()
    assert merged["GitHub"]["url"] == social_client.SITES["GitHub"]["url"]


# ── _check_site: regexCheck gate + per-site headers ─────────────────────────

def test_check_site_skips_request_for_regex_invalid_username():
    defn = {"url": "https://example.test/{username}", "error_type": "status_code",
            "error_code": 404, "regex_check": r"^[a-zA-Z0-9_]{1,15}$"}
    with patch.object(social_client, "get_http_client") as mock_get_client:
        result = _check_site("Twitter", defn, "a-username-that-is-way-too-long-for-twitter")

    mock_get_client.assert_not_called()
    assert result["found"] is False
    assert result["status"] == "invalid_username"


def test_check_site_makes_request_for_regex_valid_username():
    response = _FakeResponse('<html></html>', status_code=404, url="https://example.test/johndoe")
    defn = {"url": "https://example.test/{username}", "error_type": "status_code",
            "error_code": 404, "regex_check": r"^[a-zA-Z0-9_]{1,15}$"}
    with patch.object(social_client, "get_http_client", _client_factory(response)):
        result = _check_site("Twitter", defn, "johndoe")
    assert result["status"] == "not_found"


def test_check_site_sends_per_site_headers_merged_with_defaults():
    captured = {}

    class _CapturingClient:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def get(self, url, **kwargs):
            captured.update(kwargs.get("headers", {}))
            return _FakeResponse("<html></html>", status_code=404, url=url)

    defn = {"url": "https://example.test/{username}", "error_type": "status_code",
            "error_code": 404, "headers": {"User-Agent": "Custom/1.0"}}
    with patch.object(social_client, "get_http_client", lambda timeout=10: _CapturingClient()):
        _check_site("Example", defn, "johndoe")

    assert captured["User-Agent"] == "Custom/1.0"
    # Our own default headers (e.g. Accept-Language) are still present
    # for anything the per-site override doesn't specify.
    assert "Accept-Language" in captured


# ── Removed entries: dead/mismatched checks that should no longer exist ────

def test_removed_stale_or_mismatched_local_entries():
    for name in ("Twitter/X", "Coinbase", "Battlenet", "OkCupid",
                 "PlentyOfFish", "Zoosk", "Badoo", "Tagged", "Etherscan"):
        assert name not in social_client.SITES, f"{name} should have been removed"
