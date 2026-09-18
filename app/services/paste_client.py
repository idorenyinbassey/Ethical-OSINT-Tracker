"""Paste-site / leak monitor — searches paste-dump sites for a query
(email, username, or domain). Default provider is psbdmp.ws (keyless,
unofficial, rate-limited); an admin can configure an alternate provider's
base_url/api_key with zero code change since the request/parse logic is
isolated in _query_psbdmp.

Requires explicit opt-in (is_enabled) even though the default provider
needs no key — this hits an unofficial third-party scraper with no
documented SLA, so "works out of the box" is deliberately not the
default.
"""
import logging
from typing import Optional, List, Dict
from app.services.cache import cached
from app.repositories.api_config_repository import get_by_service
from app.utils.proxy_config import get_http_client

logger = logging.getLogger(__name__)

_DEFAULT_BASE_URL = "https://psbdmp.ws/api"


def _query_psbdmp(query: str, cfg) -> Optional[List[Dict]]:
    """Isolated request+parse for the configured paste-search provider. If
    the endpoint format has drifted by the time this runs, only this
    function needs correcting — check_pastes()'s None/[]/list contract
    stays stable for every caller (route, watchlist, tests).
    """
    base = (cfg.base_url or _DEFAULT_BASE_URL).rstrip("/")
    url = f"{base}/search/{query}"
    params = {}
    if cfg.api_key:
        params["key"] = cfg.api_key

    with get_http_client(timeout=10) as client:
        r = client.get(url, params=params)
        r.raise_for_status()
        data = r.json()

    if not isinstance(data, dict):
        return None

    matches = data.get("data") or data.get("results") or []
    if not isinstance(matches, list):
        return None

    return [
        {
            "id": m.get("id", ""),
            "url": f"https://pastebin.com/{m.get('id')}" if m.get("id") else "",
            "date": m.get("time", "") or m.get("date", ""),
            "snippet": (m.get("text") or m.get("snippet") or "")[:200],
        }
        for m in matches
        if isinstance(m, dict)
    ]


@cached(ttl=1800)
def check_pastes(query: str) -> Optional[List[Dict]]:
    """Search paste-dump sites for `query`. Returns None if the monitor
    isn't enabled or the search failed, [] for a genuine zero-hit search,
    or a list of paste hits. Never raises.
    """
    cfg = get_by_service("PasteMonitor")
    if not cfg or not cfg.is_enabled:
        return None

    try:
        return _query_psbdmp(query, cfg)
    except Exception:
        logger.exception("Paste monitor search failed for query")
        return None
