"""Canary health checks for the app's web-scraping-based data sources —
as opposed to documented JSON APIs, these depend on a third-party site's
HTML/markup staying stable, and have broken silently before (the AHMIA
anti-bot token, for one — that fix shipped only after a user reported dark
web search silently returning nothing).

Each check runs a real query against the actual service function the app
uses, chosen because it should reliably return at least one result — a
long-established dark web index term, a well-known federal corporation
that isn't going anywhere. A canary that suddenly returns zero results
usually means the site's markup changed underneath the scraper, not that
the query genuinely has no matches, so a failure here is a strong signal
the parser needs updating — not a hard guarantee, since a real outage or
rate limit looks the same from here.
"""
import logging

logger = logging.getLogger(__name__)


def _check_darkweb() -> tuple:
    from app.services.darkweb_client import search_ahmia
    # search_ahmia() is @cached(ttl=1800) for real users, which would let a
    # broken parser hide behind a real user's recent identical query for up
    # to 30 minutes — .__wrapped__ (set by functools.wraps in the cache
    # decorator) calls the real, undecorated function so this canary always
    # makes a genuinely fresh request.
    result = search_ahmia.__wrapped__("market")
    if result.get("error"):
        return False, f"error: {result['error']}"
    total = result.get("total", 0)
    return (total > 0), f"{total} result(s)"


def _check_sherlock_sites() -> tuple:
    # Deliberately bypasses social_client's in-memory/disk cache and hits
    # the live URL directly. _load_sherlock_sites() falls back to a stale
    # disk cache (up to 24h old) whenever the live GitHub fetch fails, so
    # going through it here would let a broken live fetch hide behind a
    # previously-successful cached copy indefinitely — this canary is
    # specifically about whether the *live* source is still reachable and
    # well-formed, not whether we merely have *some* usable site list.
    from app.services.social_client import _SHERLOCK_URL
    from app.utils.proxy_config import get_http_client
    with get_http_client(timeout=10) as client:
        r = client.get(_SHERLOCK_URL, follow_redirects=True)
    if r.status_code != 200:
        return False, f"HTTP {r.status_code}"
    count = len(r.json())
    # A healthy live fetch returns Sherlock's full list (600+ entries).
    # Falling below this floor usually means the response format changed,
    # not that the upstream list simply got "a bit smaller."
    return (count >= 100), f"{count} site(s) in live fetch"


def _check_company_registry_canada() -> tuple:
    from app.services.company_client import _search_canada_corporations
    result = _search_canada_corporations("Royal Bank Of Canada")
    if result.get("error"):
        return False, f"error: {result['error']}"
    found = result.get("found", [])
    return (len(found) > 0), f"{len(found)} result(s)"


_CHECKS: list = [
    ("Dark Web Search (Ahmia)", _check_darkweb),
    ("Social Search (Sherlock site list)", _check_sherlock_sites),
    ("Company Registry (Canada)", _check_company_registry_canada),
]


def run_canaries() -> list:
    """Run every registered canary check. Returns a list of
    {"name": str, "ok": bool, "detail": str}, one entry per check, in
    registration order. Never raises — a check that itself blows up
    counts as a failure with the exception as detail, rather than
    aborting the remaining checks."""
    results = []
    for name, check in _CHECKS:
        try:
            ok, detail = check()
        except Exception as exc:
            ok, detail = False, f"canary check raised: {exc}"
        results.append({"name": name, "ok": ok, "detail": detail})
    return results


def check_and_notify() -> list:
    """run_canaries(), and on any failure, send one summary notification
    via app.services.notification_service (if a webhook is configured) so
    a scraper regression is caught without anyone needing to read server
    logs. Always returns the raw results regardless of whether a
    notification was sent, configured, or even attempted."""
    results = run_canaries()
    failures = [r for r in results if not r["ok"]]
    for r in failures:
        logger.warning("Scraper canary failed: %s (%s)", r["name"], r["detail"])

    if failures:
        try:
            from app.services.notification_service import notify
            lines = "\n".join(f"- {r['name']}: {r['detail']}" for r in failures)
            notify(
                subject=f"OSINT Tracker: {len(failures)} scraper canary check(s) failing",
                body=(
                    "The following data sources returned no results on a "
                    "known-good query, which usually means the site's markup "
                    "changed and the scraper needs updating:\n" + lines
                ),
                payload={"failures": failures},
            )
        except Exception:
            logger.exception("Canary failure notification dispatch failed")

    return results
