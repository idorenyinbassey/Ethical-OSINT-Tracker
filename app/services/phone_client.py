"""Phone Lookup — free, offline enrichment via Google's libphonenumber
port (`phonenumbers`), with NumVerify (paid, if configured) layered on top
as a bonus confirmation rather than a hard requirement, plus a passive
DuckDuckGo web-mention search.

Previously this tool was entirely dead without a paid NumVerify
(apilayer.net) key: `numverify_client.validate_phone()` returns `None`
when unconfigured, and the route just showed "not configured". NumVerify's
own fields (valid/country/carrier/line_type/location) are, for most
countries, derived from the same class of bundled prefix/format data
`phonenumbers` ships offline for free — so running that first means the
tool always returns something, and a configured NumVerify key adds real
value only where it actually has better data (which its response is
allowed to override field-by-field below).

Known, inherent limitation shared by every source here (paid or free):
carrier and region lookups are prefix-based. A ported number (kept a
number while switching carriers/moving — very common in the US, UK, and
elsewhere) will not resolve to its *current* real carrier or location.
There is no free fix for this; a live HLR/carrier query is a separate paid
category (e.g. Twilio Lookup) and is out of scope here.
"""
import logging
import re
from html import unescape
from typing import Optional
from urllib.parse import parse_qs, unquote, urlparse

import phonenumbers
from phonenumbers import PhoneNumberType, carrier as pn_carrier, geocoder

from app.services import numverify_client
from app.services.cache import cached
from app.utils.proxy_config import get_http_client

logger = logging.getLogger(__name__)

_TYPE_NAMES = {
    PhoneNumberType.FIXED_LINE: "Fixed Line",
    PhoneNumberType.MOBILE: "Mobile",
    PhoneNumberType.FIXED_LINE_OR_MOBILE: "Fixed Line or Mobile",
    PhoneNumberType.TOLL_FREE: "Toll Free",
    PhoneNumberType.PREMIUM_RATE: "Premium Rate",
    PhoneNumberType.SHARED_COST: "Shared Cost",
    PhoneNumberType.VOIP: "VoIP",
    PhoneNumberType.PERSONAL_NUMBER: "Personal Number",
    PhoneNumberType.PAGER: "Pager",
    PhoneNumberType.UAN: "UAN",
    PhoneNumberType.VOICEMAIL: "Voicemail",
    PhoneNumberType.UNKNOWN: "Unknown",
}


def enrich_offline(phone: str) -> dict:
    """Validate and classify a phone number entirely offline — no network
    call, no API key, works with nothing configured in Settings. Field
    names deliberately match what NumVerify's response already used
    (valid/country_code/country_name/carrier/line_type/location) so the
    existing template and merge logic need no special-casing, plus a few
    fields NumVerify never provided (possible/e164/national_format/
    international_format).
    """
    try:
        parsed = phonenumbers.parse(phone, None)
    except phonenumbers.NumberParseException as exc:
        return {"valid": False, "possible": False,
                "error": f"'{phone}' does not look like a valid phone number ({exc})."}

    valid = phonenumbers.is_valid_number(parsed)
    ptype = phonenumbers.number_type(parsed) if valid else None
    return {
        "valid": valid,
        "possible": phonenumbers.is_possible_number(parsed),
        "country_code": phonenumbers.region_code_for_number(parsed) or "",
        "country_name": geocoder.country_name_for_number(parsed, "en") or "",
        "carrier": pn_carrier.name_for_number(parsed, "en") or "",
        "line_type": _TYPE_NAMES.get(ptype, "") if ptype is not None else "",
        "location": geocoder.description_for_number(parsed, "en") or "",
        "e164": phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164),
        "national_format": phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.NATIONAL),
        "international_format": phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL),
        "source": "offline (phonenumbers)",
    }


_DDG_HTML_URL = "https://html.duckduckgo.com/html/"
_DDG_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) OSINT-Tracker/1.0"

# DuckDuckGo's no-JS HTML results page (distinct from api.duckduckgo.com's
# Instant Answer API already used elsewhere in this app for entity lookups
# — that API only returns knowledge-panel-style summaries and has nothing
# for a raw phone number query). Free, keyless, and far more scrape-
# tolerant than Google, though its index leans on Bing + its own crawler
# rather than Google's, so coverage is real but narrower.
#
# Not independently verified against live traffic at implementation time
# — this sandbox blocks all *.duckduckgo.com domains outright. The
# result__a / result__snippet class names have been the stable markup for
# DDG's HTML endpoint for years and are the same selectors most DDG-
# scraping tools rely on, but confirm this still matches after deploying;
# a markup change degrades to an empty result list, never an exception.
#
# Attribute order in real DDG markup is `href` before `class` (e.g.
# `<a rel="nofollow" href="..." class="result__a">`), so the tag's full
# attribute string is captured first and `href` extracted from it
# separately, rather than assuming any fixed attribute order.
_RESULT_RE = re.compile(
    r'<a\s+([^>]*class="result__a"[^>]*)>(.*?)</a>.*?'
    r'<a\s+[^>]*class="result__snippet"[^>]*>(.*?)</a>',
    re.DOTALL | re.IGNORECASE,
)
_HREF_RE = re.compile(r'href="([^"]*)"', re.IGNORECASE)


def _strip_tags(html: str) -> str:
    return re.sub(r"<[^>]+>", "", html).strip()


def _resolve_ddg_redirect(href: str) -> str:
    """DDG's HTML result links point at its own /l/?uddg=<encoded-url>
    redirect, not the destination directly — decode it so the app can show
    (and later re-visit) the real target URL. Falls back to the raw href
    on any parsing hiccup, since a wrapped-but-working link is still a
    working link."""
    try:
        qs = parse_qs(urlparse(unescape(href)).query)
        real = qs.get("uddg", [None])[0]
        if real:
            return unquote(real)
    except Exception:
        pass
    return href


@cached(ttl=3600)
def search_phone_mentions(query: str, limit: int = 10) -> dict:
    """Best-effort passive web search for public mentions of a phone
    number. This is a search against a general index, not a probe against
    any single platform's own account/session/enumeration systems — the
    same reasoning that's kept this app away from live "is this number
    registered on WhatsApp" style checks elsewhere.
    """
    try:
        with get_http_client(timeout=10) as client:
            r = client.get(_DDG_HTML_URL, params={"q": f'"{query}"'},
                            headers={"User-Agent": _DDG_USER_AGENT}, follow_redirects=True)
            r.raise_for_status()
            html = r.text
    except Exception as exc:
        logger.warning("DuckDuckGo phone mention search failed for %r: %s", query, exc)
        return {"status": "error", "results": [], "total": 0}

    results = []
    for m in _RESULT_RE.finditer(html):
        title = _strip_tags(m.group(2))
        if not title:
            continue
        href_match = _HREF_RE.search(m.group(1))
        href = href_match.group(1) if href_match else ""
        results.append({
            "title": title[:150],
            "url": _resolve_ddg_redirect(href)[:300],
            "snippet": _strip_tags(m.group(3))[:300],
        })
        if len(results) >= limit:
            break

    return {"status": "ok", "results": results, "total": len(results)}


def lookup_phone(phone: str) -> dict:
    """Phone Lookup's actual entry point. Always runs the free offline
    enrichment first — this is the tool's real baseline now, not a
    fallback — and layers a configured NumVerify key's data on top,
    field by field, only where NumVerify actually returned something
    non-empty (so a paid provider's blank/absent field never blanks out
    a value the offline library already filled in). Also runs a passive
    web-mention search. Never raises; returns `{"error": ...}` only when
    the input itself isn't parseable as a phone number at all.
    """
    offline = enrich_offline(phone)
    if not offline.get("valid") and offline.get("error"):
        return offline

    result = dict(offline)
    paid = numverify_client.validate_phone(phone)
    if paid:
        for key, value in paid.items():
            if value:
                result[key] = value
        result["source"] = "NumVerify + offline enrichment"

    result["web_mentions"] = search_phone_mentions(result.get("e164") or phone)
    return result
