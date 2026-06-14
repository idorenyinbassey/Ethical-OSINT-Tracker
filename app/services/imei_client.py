"""IMEI service client — sync version."""
from typing import Optional, Dict, Any
import httpx
from app.repositories.api_config_repository import get_by_service


def _try_request(client: httpx.Client, method: str, url: str, **kwargs) -> Optional[Dict[str, Any]]:
    try:
        r = client.request(method, url, **kwargs)
        r.raise_for_status()
        try:
            return r.json()
        except Exception:
            return None
    except Exception:
        return None


def fetch_imei(imei: str, timeout: float = 5.0) -> Optional[Dict[str, Any]]:
    """Fetch IMEI details from configured IMEIService. Returns None if unavailable."""
    cfg = get_by_service("IMEIService")
    if not cfg or not cfg.is_enabled:
        return None

    base = cfg.base_url.rstrip("/")
    creds = getattr(cfg, "_credentials", {}) or {}
    api_key = cfg.api_key or creds.get("api_key") or creds.get("client_key") or creds.get("client_secret")

    endpoints = (
        f"{base}/imei",
        f"{base}/api/imei",
        f"{base}/api/v1/imei/{imei}",
        f"{base}/api/v1/imei",
        f"{base}/api/{imei}",
        f"{base}/{imei}",
    )

    headers = {}
    if api_key:
        headers = {"Authorization": f"Bearer {api_key}", "X-API-KEY": api_key}

    params_base = {"imei": imei}

    with httpx.Client(timeout=timeout) as client:
        if "imei.info" in base or "dash.imei.info" in base:
            candidate = f"{base}/api/v1/imei/{imei}"
            if api_key:
                out = _try_request(client, "GET", candidate, params={"key": api_key})
                if out:
                    return out
                out = _try_request(client, "GET", candidate, headers={"Authorization": f"Bearer {api_key}"})
                if out:
                    return out
            out = _try_request(client, "GET", candidate)
            if out:
                return out

        for ep in endpoints:
            if api_key:
                out = _try_request(client, "GET", ep, params={**params_base, "api_key": api_key}, headers=headers)
                if out:
                    return out
                out = _try_request(client, "GET", ep, params=params_base, headers=headers)
                if out:
                    return out
            out = _try_request(client, "GET", ep, params=params_base)
            if out:
                return out

    return None
