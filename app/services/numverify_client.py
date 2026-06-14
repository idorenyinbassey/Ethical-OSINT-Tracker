import httpx
from typing import Optional, Dict
from app.services.cache import cached
from app.repositories.api_config_repository import get_by_service


@cached(ttl=3600)
def validate_phone(phone: str) -> Optional[Dict]:
    """Validate phone number and get carrier info via NumVerify API."""
    cfg = get_by_service("NumVerify")
    if not cfg or not cfg.is_enabled:
        return None

    base = cfg.base_url or "http://apilayer.net/api"
    access_key = cfg.api_key
    if not access_key:
        return None

    clean = phone.replace(" ", "").replace("-", "").replace("+", "")
    url = f"{base.rstrip('/')}/validate"
    params = {"access_key": access_key, "number": clean, "country_code": "", "format": "1"}

    try:
        with httpx.Client(timeout=8) as client:
            r = client.get(url, params=params)
            r.raise_for_status()
            data = r.json()
            return {
                "valid": data.get("valid", False),
                "country_code": data.get("country_code", ""),
                "country_name": data.get("country_name", ""),
                "carrier": data.get("carrier", ""),
                "line_type": data.get("line_type", ""),
                "location": data.get("location", ""),
            }
    except Exception:
        return None
