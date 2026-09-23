import logging
import httpx
from typing import Optional, Dict, List
from app.services.cache import cached
from app.repositories.api_config_repository import get_by_service

logger = logging.getLogger(__name__)


def _cfg_and_key():
    """Shared Hunter.io config/key lookup — returns (base_url, api_key) or
    (None, None) if not configured/enabled, so every Hunter endpoint here
    degrades the same way as verify_email() already did."""
    cfg = get_by_service("Hunter.io")
    if not cfg or not cfg.is_enabled or not cfg.api_key:
        return None, None
    return (cfg.base_url or "https://api.hunter.io/v2").rstrip("/"), cfg.api_key


@cached(ttl=3600)
def verify_email(email: str) -> Optional[Dict]:
    """Verify email deliverability via Hunter.io API."""
    cfg = get_by_service("Hunter.io")
    if not cfg or not cfg.is_enabled:
        return None

    base = cfg.base_url or "https://api.hunter.io/v2"
    api_key = cfg.api_key
    if not api_key:
        return None

    url = f"{base.rstrip('/')}/email-verifier"
    params = {"email": email, "api_key": api_key}

    try:
        with httpx.Client(timeout=8) as client:
            r = client.get(url, params=params)
            r.raise_for_status()
            data = r.json().get("data", {})
            status = data.get("status", "")
            return {
                "deliverable": status == "valid",
                "disposable": data.get("disposable", False),
                "webmail": data.get("webmail", False),
                "accept_all": data.get("accept_all", False),
                "score": data.get("score", 0),
            }
    except httpx.TimeoutException:
        logger.error("Hunter.io verify timed out for %s", email)
        return None
    except httpx.HTTPStatusError as e:
        logger.error("Hunter.io HTTP %s for %s", e.response.status_code, email)
        return None
    except Exception:
        logger.exception("Hunter.io verify failed for %s", email)
        return None


@cached(ttl=3600)
def domain_search(domain: str) -> Optional[Dict]:
    """Find email addresses Hunter.io has indexed for `domain`, via its
    Domain Search endpoint. Returns None if Hunter.io isn't configured —
    a bonus enrichment on top of the free RDAP/WHOIS lookup, same pattern
    as Shodan/VirusTotal layered onto IP Lookup.
    """
    base, api_key = _cfg_and_key()
    if not base:
        return None

    url = f"{base}/domain-search"
    params = {"domain": domain, "api_key": api_key}

    try:
        with httpx.Client(timeout=8) as client:
            r = client.get(url, params=params)
            r.raise_for_status()
            data = r.json().get("data", {})
    except httpx.TimeoutException:
        logger.error("Hunter.io domain search timed out for %s", domain)
        return None
    except httpx.HTTPStatusError as e:
        logger.error("Hunter.io HTTP %s for domain search %s", e.response.status_code, domain)
        return None
    except Exception:
        logger.exception("Hunter.io domain search failed for %s", domain)
        return None

    emails: List[Dict] = []
    for entry in (data.get("emails") or [])[:20]:
        if not isinstance(entry, dict) or not entry.get("value"):
            continue
        emails.append({
            "email": entry["value"],
            "first_name": entry.get("first_name") or "",
            "last_name": entry.get("last_name") or "",
            "position": entry.get("position") or "",
            "confidence": entry.get("confidence"),
        })

    return {
        "organization": data.get("organization") or "",
        "pattern": data.get("pattern") or "",
        "total_emails": len(emails),
        "emails": emails,
    }


@cached(ttl=3600)
def find_email(domain: str, first_name: str, last_name: str) -> Optional[Dict]:
    """Guess/confirm a specific person's likely email address at `domain`
    via Hunter.io's Email Finder endpoint. Returns None if Hunter.io isn't
    configured, or {"found": False, ...} when Hunter has no confident
    match (distinct from "not configured" so the UI can show the right
    message either way).
    """
    base, api_key = _cfg_and_key()
    if not base:
        return None

    url = f"{base}/email-finder"
    params = {"domain": domain, "first_name": first_name, "last_name": last_name, "api_key": api_key}

    try:
        with httpx.Client(timeout=8) as client:
            r = client.get(url, params=params)
            r.raise_for_status()
            data = r.json().get("data", {})
    except httpx.TimeoutException:
        logger.error("Hunter.io email finder timed out for %s @ %s", first_name, domain)
        return {"found": False, "error": "Hunter.io request timed out."}
    except httpx.HTTPStatusError as e:
        logger.error("Hunter.io HTTP %s for email finder %s @ %s", e.response.status_code, first_name, domain)
        return {"found": False, "error": f"Hunter.io request failed (HTTP {e.response.status_code})."}
    except Exception:
        logger.exception("Hunter.io email finder failed for %s @ %s", first_name, domain)
        return {"found": False, "error": "Hunter.io request failed."}

    email = data.get("email")
    if not email:
        return {"found": False, "error": None}

    return {
        "found": True,
        "email": email,
        "score": data.get("score", 0),
        "position": data.get("position") or "",
    }
