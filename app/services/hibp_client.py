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


def check_password_pwned(password: str) -> int:
    """K-anonymity check via pwnedpasswords.com — returns seen count (0 = not found). No API key required."""
    import hashlib
    sha1 = hashlib.sha1(password.encode("utf-8")).hexdigest().upper()
    prefix, suffix = sha1[:5], sha1[5:]
    try:
        with httpx.Client(timeout=8) as client:
            r = client.get(f"https://api.pwnedpasswords.com/range/{prefix}",
                           headers={"User-Agent": "OSINT-Tracker", "Add-Padding": "true"})
            if r.status_code != 200:
                return -1
            for line in r.text.splitlines():
                parts = line.split(":")
                if len(parts) == 2 and parts[0].upper() == suffix:
                    return int(parts[1])
            return 0
    except Exception:
        return -1
