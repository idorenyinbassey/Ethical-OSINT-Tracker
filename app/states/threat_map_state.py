import reflex as rx
from typing import Optional
from app.repositories.investigation_repository import list_recent
from app.services.ip_client import fetch_ip


class ThreatMapState(rx.State):
    threat_markers: list[dict] = []
    is_loading: bool = False

    @rx.event
    async def load_threat_map(self):
        self.is_loading = True
        self.threat_markers = []
        yield
        # fetch recent investigations and pick IPs
        invs = list_recent(200)
        markers: list[dict] = []
        for inv in invs:
            try:
                if getattr(inv, "kind", None) != "ip":
                    continue
                ip = inv.query
                info = await fetch_ip(ip)
                if not info or info.get("lat") is None or info.get("lon") is None:
                    continue
                # derive severity from any threat_score in result_json if present
                sev = "low"
                try:
                    import json
                    data = json.loads(inv.result_json or "{}")
                    ts = int(data.get("threat_score", 0))
                    sev = "high" if ts >= 70 else ("medium" if ts >= 40 else "low")
                except Exception:
                    pass
                markers.append({
                    "ip": ip,
                    "city": info.get("city", ""),
                    "country": info.get("country", ""),
                    "asn": info.get("asn", ""),
                    "org": info.get("org", ""),
                    "lat": info["lat"],
                    "lon": info["lon"],
                    "severity": sev,
                })
            except Exception:
                continue
        self.threat_markers = markers
        self.is_loading = False
