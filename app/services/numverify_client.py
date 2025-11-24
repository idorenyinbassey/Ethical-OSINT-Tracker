import httpx
from typing import Optional, Dict
from app.services.cache import cached
from app.repositories.api_config_repository import get_by_service


@cached(ttl=3600)
async def validate_phone(phone: str) -> Optional[Dict]:
    """Validate phone number and get carrier info via NumVerify API.
    
    Normalized keys: valid, country_code, country_name, carrier, line_type, location
    Returns None if service unavailable or error.
    """
    cfg = get_by_service("NumVerify")
    if not cfg or not cfg.is_enabled:
        return None
    
    base = cfg.base_url or "http://apilayer.net/api"
    access_key = cfg.api_key
    if not access_key:
        return None
    
    # Clean phone: remove spaces, dashes, plus
    clean = phone.replace(" ", "").replace("-", "").replace("+", "")
    url = f"{base.rstrip('/')}/validate"
    params = {
        "access_key": access_key,
        "number": clean,
        "country_code": "",  # auto-detect
        "format": "1"
    }
    
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            r = await client.get(url, params=params)
            r.raise_for_status()
            data = r.json()
            
            # NumVerify response structure
            valid = data.get("valid", False)
            country_code = data.get("country_code", "")
            country_name = data.get("country_name", "")
            carrier = data.get("carrier", "")
            line_type = data.get("line_type", "")
            location = data.get("location", "")
            
            return {
                "valid": valid,
                "country_code": country_code,
                "country_name": country_name,
                "carrier": carrier,
                "line_type": line_type,
                "location": location,
            }
    except Exception:
        return None
