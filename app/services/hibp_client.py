import logging
from typing import Optional, List, Dict
from urllib.parse import quote
import httpx
from app.services.cache import cached
from app.repositories.api_config_repository import get_by_service
from app.utils.proxy_config import get_http_client

logger = logging.getLogger(__name__)

_XPOSEDORNOT_BASE_URL = "https://api.xposedornot.com/v1"


def _check_hibp(email: str, cfg) -> Optional[List[Dict]]:
    """Isolated request+parse for the real HaveIBeenPwned API — only used
    when an admin has configured a paid HIBP key (HIBP's API has had no
    free tier since 2024). Returns full breach detail (date, data
    classes, description), unlike the keyless XposedOrNot fallback.
    """
    base = cfg.base_url or "https://haveibeenpwned.com/api/v3"
    url = f"{base.rstrip('/')}/breachedaccount/{quote(email, safe='')}"
    headers = {"hibp-api-key": cfg.api_key, "User-Agent": "OSINT-Tracker"}

    try:
        with get_http_client(timeout=10) as client:
            r = client.get(url, headers=headers)
            if r.status_code == 404:
                return []
            r.raise_for_status()
            breaches = r.json()
            return [
                {
                    "name": b.get("Name", "Unknown"),
                    "date": b.get("BreachDate", ""),
                    "data_classes": b.get("DataClasses", []),
                    "description": b.get("Description", ""),
                }
                for b in breaches
            ]
    except httpx.TimeoutException:
        logger.error("HIBP breach check timed out")
        return None
    except httpx.HTTPStatusError as e:
        logger.error("HIBP HTTP %s during breach check", e.response.status_code)
        return None
    except Exception:
        logger.exception("HIBP breach check failed")
        return None


def _check_xposedornot(email: str) -> Optional[List[Dict]]:
    """Isolated request+parse for XposedOrNot's free, keyless breach-check
    API — the default when no paid HIBP key is configured. Response shape
    confirmed via XposedOrNot's own published API reference (not
    independently tested against live traffic here):
    GET /v1/check-email/{email} -> {"breaches": [["Adobe", "LinkedIn"]],
    "email": ..., "status": "success"}. Parsing also tolerates a flat
    (non-nested) list, in case the real nesting varies. Only breach names
    are available from this endpoint — no date/data_classes/description
    like HIBP provides; those fields are left empty, which the breach
    template already renders gracefully (guarded by {% if %}).

    Rate-limited to 2 req/s, 25/hour, 100/day per IP by XposedOrNot — a
    429 is treated the same as any other failure (returns None) rather
    than retried, since check_breaches() is cached for an hour anyway.
    """
    url = f"{_XPOSEDORNOT_BASE_URL}/check-email/{quote(email, safe='')}"
    try:
        with get_http_client(timeout=10) as client:
            r = client.get(url, headers={"User-Agent": "OSINT-Tracker"})
            if r.status_code == 404:
                return []
            r.raise_for_status()
            data = r.json()
    except httpx.TimeoutException:
        logger.error("XposedOrNot breach check timed out")
        return None
    except httpx.HTTPStatusError as e:
        logger.error("XposedOrNot HTTP %s during breach check", e.response.status_code)
        return None
    except Exception:
        logger.exception("XposedOrNot breach check failed")
        return None

    if not isinstance(data, dict):
        return None

    raw_breaches = data.get("breaches")
    if not raw_breaches:
        return []
    if not isinstance(raw_breaches, list):
        return None

    names: List[str] = []
    for item in raw_breaches:
        if isinstance(item, list):
            names.extend(str(n) for n in item if n)
        elif isinstance(item, str):
            names.append(item)

    return [{"name": n, "date": "", "data_classes": [], "description": ""} for n in names]


@cached(ttl=3600)
def check_breaches(email: str) -> Optional[List[Dict]]:
    """Check if `email` appears in known data breaches.

    Uses the real HaveIBeenPwned API if an admin has configured a paid
    key (HIBP's API has been paid-only since 2024 — no free tier), giving
    richer per-breach detail. Otherwise falls back automatically to
    XposedOrNot's free, keyless breach-check API — no Settings
    configuration required at all. An admin can still fully disable
    email breach checking by setting HIBP's `is_enabled` to False in
    Settings. Returns None only on a genuine failure (network error, rate
    limit, or explicitly disabled) — never raises.
    """
    cfg = get_by_service("HIBP")
    if cfg and not cfg.is_enabled:
        return None
    if cfg and cfg.api_key:
        return _check_hibp(email, cfg)
    return _check_xposedornot(email)


def check_password_pwned(password: str) -> int:
    """K-anonymity check via pwnedpasswords.com — returns seen count (0 = not found). No API key required."""
    import hashlib
    sha1 = hashlib.sha1(password.encode("utf-8")).hexdigest().upper()
    prefix, suffix = sha1[:5], sha1[5:]
    try:
        with get_http_client(timeout=8) as client:
            r = client.get(f"https://api.pwnedpasswords.com/range/{prefix}",
                           headers={"User-Agent": "OSINT-Tracker", "Add-Padding": "true"})
            if r.status_code != 200:
                return -1
            for line in r.text.splitlines():
                parts = line.split(":")
                if len(parts) == 2 and parts[0].upper() == suffix:
                    return int(parts[1])
            return 0
    except httpx.TimeoutException:
        logger.error("pwnedpasswords range check timed out")
        return -1
    except Exception:
        logger.exception("pwnedpasswords range check failed")
        return -1
