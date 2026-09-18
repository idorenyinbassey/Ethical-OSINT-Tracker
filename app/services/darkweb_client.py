"""Dark web monitoring via AHMIA.fi — indexes .onion hidden services.

AHMIA's search form embeds a dynamically-generated hidden anti-bot field
(e.g. `<input type="hidden" name="5f0c8e" value="1a76fe">` — the field
*name* itself changes per page load, not just the value). A search request
missing that field is silently redirected back to `/` with an empty body,
which is why a plain `GET /search/?q=...` always came back with zero
results. There's no public token endpoint, so the only reliable way to get
a valid token is to load the search page fresh and read it off, then reuse
it (with the same session/cookies) on the actual search request. Like any
scraper workaround for an anti-bot mechanism, this can break again if
AHMIA changes the mechanism — if that happens, this degrades to the old
empty-results behavior rather than raising.
"""
import logging
import re
import httpx
from app.services.cache import cached
from app.utils.proxy_config import get_http_client

logger = logging.getLogger(__name__)

_SEARCH_URL = "https://ahmia.fi/search/"
_HEADERS = {"User-Agent": "Mozilla/5.0 OSINT-Tracker/1.0"}

_FORM_RE = re.compile(
    r'<form[^>]+id="searchForm".*?</form>', re.DOTALL | re.IGNORECASE,
)
_HIDDEN_FIELD_RE = re.compile(
    r'<input[^>]+type="hidden"[^>]+name="([^"]+)"[^>]+value="([^"]*)"',
    re.IGNORECASE,
)


def _extract_hidden_token(html: str) -> tuple[str, str] | None:
    """Pull the anti-bot hidden field's (name, value) out of the search form."""
    form_match = _FORM_RE.search(html)
    if not form_match:
        return None
    field_match = _HIDDEN_FIELD_RE.search(form_match.group(0))
    if not field_match:
        return None
    return field_match.group(1), field_match.group(2)


@cached(ttl=1800)
def search_ahmia(query: str) -> dict:
    """Search AHMIA.fi for .onion content. Returns up to 20 results.

    On failure returns a structured dict with a generic `error`/`error_type`;
    the raw exception is logged server-side only (never surfaced to the browser).
    """
    try:
        with get_http_client(timeout=20) as client:
            params = {"q": query}
            try:
                form_page = client.get(_SEARCH_URL, headers=_HEADERS,
                                        follow_redirects=True)
                form_page.raise_for_status()
                token = _extract_hidden_token(form_page.text)
                if token:
                    params[token[0]] = token[1]
            except Exception:
                logger.warning("AHMIA anti-bot token fetch failed for %r; "
                                "searching without it", query)

            r = client.get(_SEARCH_URL, params=params, headers=_HEADERS,
                           follow_redirects=True)
            r.raise_for_status()
            return _parse_ahmia(r.text, query)
    except httpx.TimeoutException:
        logger.error("AHMIA search timed out for %r", query)
        return {"query": query, "results": [], "error_type": "timeout",
                "error": "AHMIA request timed out. Try again."}
    except httpx.HTTPStatusError as e:
        logger.error("AHMIA HTTP %s for %r", e.response.status_code, query)
        return {"query": query, "results": [], "error_type": "http_error",
                "error": "AHMIA request failed. Try again."}
    except Exception:
        logger.exception("AHMIA search failed for %r", query)
        return {"query": query, "results": [], "error_type": "unknown",
                "error": "AHMIA search failed. Try again."}


def _parse_ahmia(html: str, query: str) -> dict:
    results = []
    # Current AHMIA template wraps each hit in <li class="result">...</li>,
    # with a title link, a description <p>, and a domain <cite>.
    pattern = re.compile(
        r'<li[^>]+class="result"[^>]*>.*?'
        r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>.*?'
        r'<p[^>]*>(.*?)</p>',
        re.DOTALL | re.IGNORECASE,
    )
    for m in pattern.finditer(html):
        href = m.group(1).strip()
        title = re.sub(r"<[^>]+>", "", m.group(2)).strip()
        desc = re.sub(r"<[^>]+>", "", m.group(3)).strip()
        if not title:
            continue
        # The real .onion URL is carried in the redirect_url= query param.
        onion_match = re.search(r'redirect_url=(https?://[a-z2-7]+\.onion[^\s"&]*)', href)
        onion_url = onion_match.group(1) if onion_match else href
        results.append({"title": title[:120], "url": onion_url[:200], "description": desc[:300]})
        if len(results) >= 20:
            break

    return {
        "query": query,
        "results": results,
        "total": len(results),
        "source": "ahmia.fi",
    }
