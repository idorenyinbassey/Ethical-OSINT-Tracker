"""app.services.social_client._extract_contact_info — best-effort scraping
of contact-relevant signals (emails, rel="me" cross-linked profiles) from
an already-fetched, confirmed-found profile page. Deliberately narrow in
scope: emails only come from mailto: links and the OG/Twitter bio text
(never raw HTML, to avoid tracking-script noise), and cross-links only
come from the high-confidence rel="me" convention, not arbitrary URLs."""
from app.services.social_client import _extract_contact_info


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
