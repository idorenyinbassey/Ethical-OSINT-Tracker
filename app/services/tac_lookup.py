"""Offline IMEI/TAC lookup — free, no API key, no network call required, no
credits to run out.

A device's Type Allocation Code (TAC) is the first 8 digits of its IMEI and
identifies the manufacturer/model. Ships a static, install-time snapshot of
a TAC-to-device database (~255k entries, MIT-licensed, from
github.com/MoazEb/tac-database) so brand/model lookups keep working even
when no paid IMEIService key is configured or its credits have run out —
the exact complaint that led to this fallback. It can't tell you
blacklist/stolen/warranty status: that data lives behind carrier/GSMA
agreements and isn't available for free from anyone legitimately, so that
detail still requires a paid provider.

refresh_tac_database() optionally re-downloads a newer copy of the same
database into a writable, install-independent location, so the bundled
snapshot doesn't just get staler forever. A failed or skipped refresh is
never fatal — lookups always fall back to the read-only bundled copy.
"""
import csv
import gzip
import logging
import os
import re
import time
from pathlib import Path
from typing import Optional, Dict

logger = logging.getLogger(__name__)

_BUNDLED_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "tac_database.csv.gz"

_SOURCE_URL = "https://raw.githubusercontent.com/MoazEb/tac-database/main/tac_full.csv"
_EXPECTED_HEADER = "Brand,TAC,SPECS"
_MIN_PLAUSIBLE_ROWS = 50_000

_tac_db: Optional[Dict[str, Dict[str, str]]] = None


def _writable_db_path() -> Path:
    data_dir = os.getenv("OSINT_TRACKER_DATA_DIR")
    base = Path(data_dir) if data_dir else Path.home() / ".local" / "share" / "osint-tracker"
    return base / "tac_database.csv.gz"


def _parse_db_file(path: Path) -> Dict[str, Dict[str, str]]:
    db: Dict[str, Dict[str, str]] = {}
    try:
        with gzip.open(path, mode="rt", encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                tac = (row.get("TAC") or "").strip()
                if tac and tac not in db:
                    db[tac] = {
                        "brand": (row.get("Brand") or "").strip(),
                        "specs": (row.get("SPECS") or "").strip(),
                    }
    except (OSError, csv.Error, EOFError, gzip.BadGzipFile):
        return {}
    return db


def _load_db() -> Dict[str, Dict[str, str]]:
    global _tac_db
    if _tac_db is not None:
        return _tac_db
    # Prefer a refreshed copy (if refresh_tac_database() ever succeeded);
    # fall back to the bundled, read-only, install-time snapshot so
    # offline lookup can never end up with zero data.
    for path in (_writable_db_path(), _BUNDLED_DB_PATH):
        db = _parse_db_file(path)
        if db:
            _tac_db = db
            return db
    _tac_db = {}
    return _tac_db


def invalidate_cache() -> None:
    """Force the next lookup_tac() call to reload from disk."""
    global _tac_db
    _tac_db = None


def refresh_tac_database(min_age_days: float = 1.0, timeout: float = 30.0) -> bool:
    """Re-download the TAC database into the writable path if the local
    copy is missing or older than min_age_days. Never raises — a failed
    or skipped refresh just leaves the existing (writable or bundled)
    data in place. Returns True only on a successful, applied refresh."""
    if os.getenv("TAC_DB_AUTO_UPDATE", "true").strip().lower() in ("0", "false", "no"):
        return False

    path = _writable_db_path()
    try:
        if path.exists():
            age_days = (time.time() - path.stat().st_mtime) / 86400
            if age_days < min_age_days:
                return False
    except OSError:
        pass

    try:
        from app.utils.proxy_config import get_http_client
        with get_http_client(timeout=timeout) as client:
            r = client.get(_SOURCE_URL)
            r.raise_for_status()
            text = r.text
    except Exception:
        logger.warning("TAC database refresh failed to download", exc_info=True)
        return False

    if not text.lstrip().startswith(_EXPECTED_HEADER):
        logger.warning("TAC database refresh got unexpected format, keeping existing data")
        return False

    row_count = text.count("\n") - 1
    if row_count < _MIN_PLAUSIBLE_ROWS:
        logger.warning("TAC database refresh returned suspiciously few rows (%d), keeping existing data", row_count)
        return False

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        with gzip.open(tmp, mode="wt", encoding="utf-8", newline="") as f:
            f.write(text)
        os.replace(tmp, path)
    except OSError:
        logger.warning("TAC database refresh could not write to %s", path, exc_info=True)
        return False

    invalidate_cache()
    logger.info("TAC database refreshed (%d rows) at %s", row_count, path)
    return True


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
