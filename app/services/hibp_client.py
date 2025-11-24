import httpx
from typing import Optional, List, Dict
from app.services.cache import cached
from app.repositories.api_config_repository import get_by_service


@cached(ttl=3600)
async def check_breaches(email: str) -> Optional[List[Dict]]:
    """Check if email appears in known data breaches via HaveIBeenPwned API.
    
    Returns list of breach dicts with: Name, BreachDate, DataClasses, Description
    Returns None if service unavailable or error.
    """
    cfg = get_by_service("HIBP")
    if not cfg or not cfg.is_enabled:
        return None
    
    base = cfg.base_url or "https://haveibeenpwned.com/api/v3"
    api_key = cfg.api_key
    if not api_key:
        return None
    
    url = f"{base.rstrip('/')}/breachedaccount/{email}"
    headers = {
        "hibp-api-key": api_key,
        "User-Agent": "OSINT-Tracker"
    }
    
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url, headers=headers)
            if r.status_code == 404:
                # No breaches found (clean account)
                return []
            r.raise_for_status()
            breaches = r.json()
            # Normalize to relevant fields
            result = []
            for b in breaches:
                result.append({
                    "name": b.get("Name", "Unknown"),
                    "date": b.get("BreachDate", ""),
                    "data_classes": b.get("DataClasses", []),
                    "description": b.get("Description", ""),
                })
            return result
    except Exception:
        return None
