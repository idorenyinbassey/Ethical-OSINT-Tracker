"""IMEI service client — sync version."""
from typing import Optional, Dict, Any
from app.repositories.api_config_repository import get_by_service
from app.utils.proxy_config import get_http_client


def fetch_imei(imei: str, timeout: float = 10.0) -> Dict[str, Any]:
    """Fetch IMEI details from configured IMEIService.

    Always returns a dict. On failure, the dict contains an 'error' key.
    If not configured at all, also sets 'not_configured': True.
    """
    cfg = get_by_service("IMEIService")
    if not cfg:
        return {"error": "IMEI Service not configured. Add API key and base URL in Settings.", "not_configured": True}
    if not cfg.is_enabled:
        return {"error": "IMEI Service is disabled. Enable it in Settings.", "not_configured": True}

    base = (cfg.base_url or "").rstrip("/")
    if not base:
        return {"error": "IMEI Service base URL is missing. Set it in Settings (e.g. https://api.imei.info).", "not_configured": True}

    creds = getattr(cfg, "_credentials", {}) or {}
    api_key = cfg.api_key or creds.get("api_key") or creds.get("client_key") or creds.get("client_secret")
    if not api_key:
        return {"error": "IMEI API key is missing. Enter your key in Settings.", "not_configured": True}

    headers: dict = {}
    if api_key:
        headers = {"Authorization": f"Bearer {api_key}", "X-API-KEY": api_key}

    last_error = "All endpoint attempts failed."
    try:
        with get_http_client(timeout=timeout) as client:
            # imei.info specific — try v2 first, then v1
            if "imei.info" in base:
                for version in ("v2", "v1"):
                    url = f"{base}/api/{version}/imei/{imei}"
                    for params in ({"key": api_key}, {}):
                        try:
                            r = client.get(url, params=params, headers=headers)
                            if r.status_code == 200:
                                data = r.json()
                                if data:
                                    return data
                            elif r.status_code == 401:
                                return {"error": f"IMEI API key rejected (HTTP 401). Check your key in Settings."}
                            elif r.status_code == 403:
                                return {"error": f"IMEI API key forbidden (HTTP 403). Your plan may not cover this query."}
                            else:
                                last_error = f"HTTP {r.status_code} from {url}"
                        except Exception as exc:
                            last_error = str(exc)

            # Generic fallback endpoints
            endpoints = [
                f"{base}/api/v2/imei/{imei}",
                f"{base}/api/v1/imei/{imei}",
                f"{base}/imei/{imei}",
                f"{base}/api/imei",
                f"{base}/imei",
                f"{base}/{imei}",
            ]
            params_base = {"imei": imei}
            for ep in endpoints:
                for req_params in (
                    {**params_base, "key": api_key},
                    {**params_base, "api_key": api_key},
                    params_base,
                ):
                    try:
                        r = client.get(ep, params=req_params, headers=headers)
                        if r.status_code == 200:
                            data = r.json()
                            if data and not data.get("error"):
                                return data
                        elif r.status_code in (401, 403):
                            return {"error": f"IMEI API authentication failed (HTTP {r.status_code}). Check key in Settings."}
                        else:
                            last_error = f"HTTP {r.status_code} from {ep}"
                    except Exception as exc:
                        last_error = str(exc)
    except Exception as exc:
        return {"error": f"IMEI connection error: {exc}"}

    return {"error": f"IMEI lookup failed: {last_error}"}
