"""Build a STIX 2.1 bundle from a case's investigations.

No external stix2 library required — we construct the JSON directly.
"""
import json
import uuid
import datetime
from typing import List


def _uid(type_name: str) -> str:
    return f"{type_name}--{uuid.uuid4()}"


def _ts() -> str:
    return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _observable(inv) -> dict | None:
    kind = (inv.kind or "").lower()
    q = (inv.query or "").strip()
    if not q:
        return None

    if kind == "ip":
        # Try IPv6 vs IPv4
        t = "ipv6-addr" if ":" in q else "ipv4-addr"
        return {"type": t, "id": _uid(t), "spec_version": "2.1", "value": q}

    if kind == "domain":
        return {"type": "domain-name", "id": _uid("domain-name"), "spec_version": "2.1", "value": q}

    if kind == "email":
        return {"type": "email-addr", "id": _uid("email-addr"), "spec_version": "2.1", "value": q}

    if kind == "social":
        return {"type": "user-account", "id": _uid("user-account"), "spec_version": "2.1",
                "user_id": q, "account_type": "unknown"}

    if kind in ("url", "darkweb"):
        return {"type": "url", "id": _uid("url"), "spec_version": "2.1", "value": q}

    if kind == "file":
        return {"type": "file", "id": _uid("file"), "spec_version": "2.1", "name": q}

    if kind == "crypto":
        return {"type": "x-osint-crypto-wallet", "id": _uid("x-osint-crypto-wallet"),
                "spec_version": "2.1", "address": q}

    if kind == "phone":
        return {"type": "x-osint-phone", "id": _uid("x-osint-phone"),
                "spec_version": "2.1", "number": q}

    if kind == "imei":
        return {"type": "x-osint-device", "id": _uid("x-osint-device"),
                "spec_version": "2.1", "imei": q}

    # Generic fallback
    return {"type": "x-osint-artifact", "id": _uid("x-osint-artifact"),
            "spec_version": "2.1", "kind": kind, "value": q}


def export_stix(case, investigations: List) -> bytes:
    now = _ts()
    objects = []
    ref_ids = []

    for inv in investigations:
        obs = _observable(inv)
        if obs:
            objects.append(obs)
            ref_ids.append(obs["id"])

            # Add an Indicator wrapping it
            kind = (inv.kind or "").lower()
            q = (inv.query or "").strip()
            pattern = f"[network-traffic:dst_ref.value = '{q}']" if kind == "ip" else f"[{obs['type']}:value = '{q}']" if obs.get("value") else None
            if pattern:
                ind_id = _uid("indicator")
                ind = {
                    "type": "indicator",
                    "id": ind_id,
                    "spec_version": "2.1",
                    "created": now,
                    "modified": now,
                    "name": f"{kind.upper()} – {q}",
                    "pattern": pattern,
                    "pattern_type": "stix",
                    "valid_from": now,
                    "indicator_types": ["unknown"],
                }
                objects.append(ind)
                ref_ids.append(ind_id)

                # Relationship: indicator indicates observable
                rel = {
                    "type": "relationship",
                    "id": _uid("relationship"),
                    "spec_version": "2.1",
                    "created": now,
                    "modified": now,
                    "relationship_type": "indicates",
                    "source_ref": ind_id,
                    "target_ref": obs["id"],
                }
                objects.append(rel)
                ref_ids.append(rel["id"])

    # Report object
    report = {
        "type": "report",
        "id": _uid("report"),
        "spec_version": "2.1",
        "created": now,
        "modified": now,
        "name": getattr(case, "title", "OSINT Case Report"),
        "description": getattr(case, "description", "") or "",
        "published": now,
        "report_types": ["threat-report"],
        "object_refs": ref_ids or ["indicator--" + str(uuid.uuid4())],
    }
    objects.insert(0, report)

    bundle = {
        "type": "bundle",
        "id": _uid("bundle"),
        "objects": objects,
    }
    return json.dumps(bundle, indent=2).encode("utf-8")
