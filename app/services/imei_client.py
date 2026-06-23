"""IMEI service client — imei.info dash API (https://dash.imei.info/api)."""
from typing import Dict, Any
from app.repositories.api_config_repository import get_by_service
from app.utils.proxy_config import get_http_client


def fetch_imei(imei: str, timeout: float = 10.0) -> Dict[str, Any]:
    cfg = get_by_service("IMEIService")
    if not cfg:
        return {"error": "IMEI Service not configured. Add API key and base URL in Settings.", "not_configured": True}
    if not cfg.is_enabled:
        return {"error": "IMEI Service is disabled. Enable it in Settings.", "not_configured": True}

    base = (cfg.base_url or "").rstrip("/")
    if not base:
        return {"error": "IMEI Service base URL is missing. Set it to https://dash.imei.info/api in Settings.", "not_configured": True}

    api_key = cfg.api_key
    if not api_key:
        return {"error": "IMEI API key is missing. Enter your key in Settings.", "not_configured": True}

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }

    # imei.info dash API endpoints to try in order
    endpoints = [
        f"{base}/imei-detect/{imei}/",
        f"{base}/imei-detect/{imei}",
        f"{base}/imei/{imei}/",
        f"{base}/imei/{imei}",
        f"{base}/check/{imei}/",
    ]

    try:
        with get_http_client(timeout=timeout) as client:
            for url in endpoints:
                try:
                    r = client.get(url, headers=headers)
                    if r.status_code == 200:
                        data = r.json()
                        if data:
                            return data
                    elif r.status_code == 401:
                        return {"error": "IMEI API key rejected (HTTP 401). Check your key in Settings."}
                    elif r.status_code == 403:
                        return {"error": "IMEI API key forbidden (HTTP 403). Ensure your account has a funded balance ($5 minimum on imei.info)."}
                    elif r.status_code == 402:
                        return {"error": "Insufficient balance (HTTP 402). Fund your imei.info account to make API requests."}
                except Exception as exc:
                    last = str(exc)
                    continue
    except Exception as exc:
        return {"error": f"IMEI connection error: {exc}"}

    return {"error": f"IMEI lookup failed. Verify the base URL ({base}) and your account balance at dash.imei.info."}
