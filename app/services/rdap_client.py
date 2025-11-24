import httpx
from typing import Optional, Dict
from app.services.cache import cached


@cached(ttl=24 * 3600)
async def fetch_domain(domain: str) -> Optional[Dict]:
    """Fetch domain registration data from public RDAP (no key required).

    Returns a normalized dict with keys: registrar, status, ns, created, expires
    On error, returns None (caller should fallback to mock).
    """
    url = f"https://rdap.org/domain/{domain}"
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(url)
            r.raise_for_status()
            data = r.json()

            registrar = None
            if "entities" in data:
                for ent in data["entities"]:
                    roles = ent.get("roles", [])
                    if "registrar" in roles:
                        v = ent.get("vcardArray", [])
                        if isinstance(v, list) and len(v) > 1:
                            # vcardArray[1] is list of items [name, params, value]
                            for item in v[1]:
                                if len(item) >= 3 and item[0] == "fn":
                                    registrar = item[3] if len(item) > 3 else item[2]
                                    break
                        break

            status = None
            if "status" in data and isinstance(data["status"], list) and data["status"]:
                status = data["status"][0]

            nservers = []
            for ns in data.get("nameservers", []) or []:
                ldhName = ns.get("ldhName")
                if ldhName:
                    nservers.append(ldhName)

            created = None
            expires = None
            for ev in data.get("events", []) or []:
                if ev.get("eventAction") == "registration":
                    created = ev.get("eventDate")
                if ev.get("eventAction") == "expiration":
                    expires = ev.get("eventDate")

            return {
                "registrar": registrar or "Unknown Registrar",
                "status": status or "active",
                "ns": nservers,
                "created": created or "",
                "expires": expires or "",
            }
    except Exception:
        return None
