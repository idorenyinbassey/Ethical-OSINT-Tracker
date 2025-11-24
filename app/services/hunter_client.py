import httpx
from typing import Optional, Dict
from app.services.cache import cached
from app.repositories.api_config_repository import get_by_service


@cached(ttl=3600)
async def verify_email(email: str) -> Optional[Dict]:
    """Verify email deliverability and disposable status via Hunter.io API.
    
    Normalized keys: deliverable, disposable, webmail, accept_all, score
    Returns None if service unavailable or error.
    """
    cfg = get_by_service("Hunter.io")
    if not cfg or not cfg.is_enabled:
        return None
    
    base = cfg.base_url or "https://api.hunter.io/v2"
    api_key = cfg.api_key
    if not api_key:
        return None
    
    url = f"{base.rstrip('/')}/email-verifier"
    params = {
        "email": email,
        "api_key": api_key
    }
    
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            r = await client.get(url, params=params)
            r.raise_for_status()
            data = r.json().get("data", {})
            
            # Hunter.io response structure
            status = data.get("status", "")
            deliverable = status == "valid"
            disposable = data.get("disposable", False)
            webmail = data.get("webmail", False)
            accept_all = data.get("accept_all", False)
            score = data.get("score", 0)
            
            return {
                "deliverable": deliverable,
                "disposable": disposable,
                "webmail": webmail,
                "accept_all": accept_all,
                "score": score,
            }
    except Exception:
        return None
