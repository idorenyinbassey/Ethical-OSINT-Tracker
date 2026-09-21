"""Leak monitor — searches Hudson Rock's free Cavalier Community API for
infostealer/compromised-credential intelligence matching a query (email,
username, or domain). Keyless — no signup or API key required, unlike
the previous provider (psbdmp.ws, a paste-dump scraper that has since
shut down permanently). Runs by default with no Settings configuration
at all (see check_pastes()) — an admin can still point base_url/api_key
at a different provider, or explicitly disable it, with zero change to
check_pastes()'s contract, since the actual request/parse is isolated in
_query_cavalier.

Note this is a genuine change in data source, not just a URL swap: this
returns infostealer infection intelligence (which compromised computers
leaked credentials for this email/username/domain), not literal
paste-site dumps. Still fits "leak monitor" — just no longer literally
"paste site" data.
"""
import logging
from typing import Optional, List, Dict
from app.services.cache import cached
from app.repositories.api_config_repository import get_by_service
from app.utils.proxy_config import get_http_client
from app.utils.validators import classify_query_kind

logger = logging.getLogger(__name__)

_DEFAULT_BASE_URL = "https://cavalier.hudsonrock.com/api/json/v2/osint-tools"

_ENDPOINT_BY_KIND = {
    "email": "search-by-email",
    "domain": "search-by-domain",
    "username": "search-by-username",
}


def _query_cavalier(query: str, cfg) -> Optional[List[Dict]]:
    """Isolated request+parse for the configured leak-search provider.

    Hudson Rock's exact response schema is not independently verified
    against live traffic (their docs site was unreachable at
    implementation time — this is built from secondhand documentation
    summaries). Parsing is deliberately defensive: unexpected shapes
    degrade to "no results" rather than raising, and both a bare list
    and several plausible dict-wrapper keys are accepted for the
    top-level response. If the real shape differs, only this function
    needs correcting — check_pastes()'s None/[]/list contract stays
    stable for every caller (route, watchlist, tests).

    Never re-surfaces the actual captured username/password from a
    stealer log — this tool flags exposure, it doesn't redisplay
    harvested credentials.
    """
    base = ((cfg.base_url if cfg else None) or _DEFAULT_BASE_URL).rstrip("/")
    endpoint = _ENDPOINT_BY_KIND[classify_query_kind(query)]
    param_name = endpoint.rsplit("-", 1)[-1]  # "email" / "domain" / "username"
    url = f"{base}/{endpoint}"
    params = {param_name: query}
    if cfg and cfg.api_key:
        params["key"] = cfg.api_key

    with get_http_client(timeout=10) as client:
        r = client.get(url, params=params)
        r.raise_for_status()
        data = r.json()

    if isinstance(data, list):
        stealers = data
    elif isinstance(data, dict):
        stealers = data.get("stealers") or data.get("data") or data.get("results") or []
    else:
        return None

    if not isinstance(stealers, list):
        return None

    hits: List[Dict] = []
    for entry in stealers:
        if not isinstance(entry, dict):
            continue
        date = entry.get("date_compromised") or entry.get("date_uploaded") or ""
        stealer_family = entry.get("stealer_family") or entry.get("stealer") or "Unknown stealer"
        credentials = entry.get("credentials")
        if isinstance(credentials, list) and credentials:
            for cred in credentials[:10]:
                if not isinstance(cred, dict):
                    continue
                cred_domain = cred.get("domain") or ""
                hits.append({
                    "id": "",
                    "url": cred.get("url") or "",
                    "date": date,
                    "snippet": (
                        f"{stealer_family} infection — credentials captured for {cred_domain}"
                        if cred_domain else f"{stealer_family} infection"
                    ),
                })
        else:
            hits.append({
                "id": "",
                "url": "",
                "date": date,
                "snippet": f"{stealer_family} infection on a compromised computer",
            })
    return hits


@cached(ttl=1800)
def check_pastes(query: str) -> Optional[List[Dict]]:
    """Search Hudson Rock's infostealer/leak intelligence for `query`
    (email, username, or domain). The underlying Cavalier API is free and
    keyless, so this runs by default with no Settings configuration at
    all — mirroring hibp_client's pattern, an admin can still fully
    disable it by setting PasteMonitor's `is_enabled` to False, or point
    `base_url`/`api_key` at a different provider. Returns None if
    explicitly disabled or the search failed, [] for a genuine zero-hit
    search, or a list of hits. Never raises.
    """
    cfg = get_by_service("PasteMonitor")
    if cfg and not cfg.is_enabled:
        return None

    try:
        return _query_cavalier(query, cfg)
    except Exception:
        logger.exception("Leak monitor search failed for query")
        return None
