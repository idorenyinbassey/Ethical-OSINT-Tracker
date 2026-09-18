"""Offline IMEI/TAC lookup — free, no API key, no network call, no credits to run out.

A device's Type Allocation Code (TAC) is the first 8 digits of its IMEI and
identifies the manufacturer/model. Bundles a static TAC-to-device database
(~255k entries, MIT-licensed, from github.com/MoazEb/tac-database) so brand
and model lookups keep working even when no paid IMEIService key is
configured or its credits have run out — the exact complaint that led to
this fallback. It can't tell you blacklist/stolen/warranty status: that
data lives behind carrier/GSMA agreements and isn't available for free
from anyone legitimately, so that detail still requires a paid provider.
"""
import csv
import gzip
import re
from pathlib import Path
from typing import Optional, Dict

_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "tac_database.csv.gz"

_tac_db: Optional[Dict[str, Dict[str, str]]] = None


def _load_db() -> Dict[str, Dict[str, str]]:
    global _tac_db
    if _tac_db is not None:
        return _tac_db
    db: Dict[str, Dict[str, str]] = {}
    try:
        with gzip.open(_DB_PATH, mode="rt", encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                tac = (row.get("TAC") or "").strip()
                if tac and tac not in db:
                    db[tac] = {
                        "brand": (row.get("Brand") or "").strip(),
                        "specs": (row.get("SPECS") or "").strip(),
                    }
    except (OSError, csv.Error):
        db = {}
    _tac_db = db
    return db


def luhn_valid(imei: str) -> bool:
    """Validate a 15-digit IMEI's Luhn check digit (last digit)."""
    digits = [int(c) for c in imei]
    odd = digits[-1::-2]
    even = digits[-2::-2]
    total = sum(odd) + sum(sum(divmod(d * 2, 10)) for d in even)
    return total % 10 == 0


def lookup_tac(imei_or_tac: str) -> dict:
    """Look up the manufacturer/model for an IMEI or bare TAC from the
    offline database. Always returns a dict — never raises, never hits
    the network."""
    digits = re.sub(r"\D", "", imei_or_tac or "")
    tac = digits[:8]
    result = {
        "imei": digits if len(digits) >= 14 else None,
        "tac": tac,
        "source": "offline TAC database (free, no key required)",
    }
    if len(digits) == 15:
        result["luhn_valid"] = luhn_valid(digits)

    entry = _load_db().get(tac)
    if entry:
        result["brand"] = entry["brand"]
        result["model"] = entry["specs"]
    else:
        result["note"] = (
            "TAC not found in the offline database. Blacklist, stolen, and "
            "warranty status are never free — configure a paid IMEIService "
            "key in Settings for that level of detail."
        )
    return result
