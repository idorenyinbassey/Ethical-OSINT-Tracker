"""IMEI service client.

This client attempts to call a configured IMEI service (configured via
`APIConfig` with service_name `IMEIService`). If a live service is not
configured or the call fails, the client returns None so callers can
fall back to local deterministic mock data.

The expected config values (example) are:
  - base_url: https://api.imei.info
  - api_key in `api_key` field or `client_key`/`client_secret` in `credentials`

This implementation performs a simple GET request; adapt to the real
provider's API shape when wiring a specific vendor.
"""
from typing import Optional, Dict, Any, Iterable
import httpx
from app.repositories.api_config_repository import get_by_service


async def _try_request(client: httpx.AsyncClient, method: str, url: str, **kwargs) -> Optional[Dict[str, Any]]:
    try:
        r = await client.request(method, url, **kwargs)
        r.raise_for_status()
        try:
            return r.json()
        except Exception:
            return None
    except Exception:
        return None


async def fetch_imei(imei: str, timeout: float = 5.0) -> Optional[Dict[str, Any]]:
    """Try to fetch IMEI details from configured IMEIService.

    This function attempts multiple common endpoint shapes and auth
    methods (query param, header) to increase compatibility with
    providers such as dash.imei.info. Returns provider JSON on success
    or None on failure.
    """
    cfg = get_by_service("IMEIService")
    if not cfg or not cfg.is_enabled:
        return None

    base = cfg.base_url.rstrip("/")
    creds = getattr(cfg, "_credentials", {}) or {}
    api_key = cfg.api_key or creds.get("api_key") or creds.get("client_key") or creds.get("client_secret")

    # Candidate endpoint patterns to try (path templates)
    endpoints: Iterable[str] = (
        f"{base}/imei",
        f"{base}/api/imei",
        f"{base}/api/v1/imei/{imei}",
        f"{base}/api/v1/imei",
        f"{base}/api/{imei}",
        f"{base}/{imei}",
    )

    headers = {}
    if api_key:
        # Try common header styles
        headers.update({"Authorization": f"Bearer {api_key}", "X-API-KEY": api_key})

    params_base = {"imei": imei}

    async with httpx.AsyncClient(timeout=timeout) as client:
        # First try provider-specific quick path for imei.info (dash.imei.info)
        if "imei.info" in base or "dash.imei.info" in base:
            # Known pattern: dash.imei.info often expects path like /api/v1/{imei} or /api/imei
            candidate = f"{base}/api/v1/imei/{imei}"
            if api_key:
                # try with api_key as query param
                out = await _try_request(client, "GET", candidate, params={"key": api_key})
                if out:
                    return out
                out = await _try_request(client, "GET", candidate, headers={"Authorization": f"Bearer {api_key}"})
                if out:
                    return out
            # try without key
            out = await _try_request(client, "GET", candidate)
            if out:
                return out

        # Generic attempts: try endpoints with api_key as param, then headers, then without
        for ep in endpoints:
            if api_key:
                out = await _try_request(client, "GET", ep, params={**params_base, "api_key": api_key}, headers=headers)
                if out:
                    return out
                out = await _try_request(client, "GET", ep, params=params_base, headers=headers)
                if out:
                    return out
            out = await _try_request(client, "GET", ep, params=params_base)
            if out:
                return out

    return None
