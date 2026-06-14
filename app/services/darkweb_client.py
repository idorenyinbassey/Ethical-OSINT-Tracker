"""Dark web monitoring via AHMIA.fi — indexes .onion hidden services."""
import re
import httpx
from app.services.cache import cached


@cached(ttl=1800)
def search_ahmia(query: str) -> dict:
    """Search AHMIA.fi for .onion content. Returns up to 20 results."""
    url = "https://ahmia.fi/search/"
    try:
        with httpx.Client(timeout=20, follow_redirects=True) as client:
            r = client.get(url, params={"q": query},
                           headers={"User-Agent": "Mozilla/5.0 OSINT-Tracker/1.0"})
            r.raise_for_status()
            return _parse_ahmia(r.text, query)
    except httpx.TimeoutException:
        return {"query": query, "results": [], "error": "AHMIA request timed out. Try again."}
    except Exception as exc:
        return {"query": query, "results": [], "error": str(exc)}


def _parse_ahmia(html: str, query: str) -> dict:
    results = []
    # Match result blocks: each has an h4 with a link and a following description
    pattern = re.compile(
        r'<h4[^>]*>.*?<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>.*?</h4>'
        r'.*?<p[^>]*>(.*?)</p>',
        re.DOTALL | re.IGNORECASE,
    )
    for m in pattern.finditer(html):
        href = m.group(1).strip()
        title = re.sub(r"<[^>]+>", "", m.group(2)).strip()
        desc = re.sub(r"<[^>]+>", "", m.group(3)).strip()
        if not title:
            continue
        # Extract .onion URL from redirect link if present
        onion_match = re.search(r'jump=(https?://[a-z2-7]+\.onion[^\s"&]*)', href)
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
