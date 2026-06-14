import httpx
from typing import Optional, List, Dict
from app.services.cache import cached
from app.repositories.api_config_repository import get_by_service


@cached(ttl=3600)
def check_breaches(email: str) -> Optional[List[Dict]]:
    """Check if email appears in known data breaches via HaveIBeenPwned API."""
    cfg = get_by_service("HIBP")
    if not cfg or not cfg.is_enabled:
        return None

    base = cfg.base_url or "https://haveibeenpwned.com/api/v3"
    api_key = cfg.api_key
    if not api_key:
        return None

    url = f"{base.rstrip('/')}/breachedaccount/{email}"
    headers = {"hibp-api-key": api_key, "User-Agent": "OSINT-Tracker"}

    try:
        with httpx.Client(timeout=10) as client:
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
    except Exception:
        return None
