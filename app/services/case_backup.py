"""Per-case encrypted backup/restore.

Bundles a case's investigations, comments, notes, watchlist targets, and
tracking links (with their hits) into a single AES-256-encrypted zip, and
restores that same bundle back into a case with each record's original
timestamp preserved — so closing a case (which cascades to delete its
data) doesn't have to mean losing it forever, as long as a backup was
taken first.

Uses pyzipper for real AES-256 zip encryption; the stdlib zipfile module
only supports the legacy, crackable ZipCrypto scheme. The password is
supplied by the caller at download/restore time and is never stored
anywhere by this app.
"""
import datetime
import io
import json
import secrets

import pyzipper
from sqlmodel import select

from app.repositories.base import session_scope
from app.models.investigation import Investigation
from app.models.case_comment import CaseComment
from app.models.case_note import CaseNote
from app.models.watchlist import WatchlistTarget
from app.models.tracking_link import TrackingLink
from app.models.tracking_hit import TrackingHit

_MANIFEST_VERSION = 1


class WrongPasswordError(Exception):
    """Raised when a restore zip can't be decrypted with the given password."""


class InvalidBackupError(Exception):
    """Raised when a decrypted backup's contents aren't in the expected shape."""


def _iso(dt) -> str | None:
    return dt.isoformat() if dt else None


def _parse_iso(s) -> datetime.datetime | None:
    return datetime.datetime.fromisoformat(s) if s else None


# ── Gather (dump) ────────────────────────────────────────────────────────────

def _dump_investigations(session, case_id: int) -> list[dict]:
    rows = session.exec(select(Investigation).where(Investigation.case_id == case_id)).all()
    return [
        {
            "kind": r.kind, "query": r.query, "result_json": r.result_json,
            "confidence": r.confidence, "tags": r.tags,
            "created_at": _iso(r.created_at), "updated_at": _iso(r.updated_at),
        }
        for r in rows
    ]


def _dump_comments(session, case_id: int) -> list[dict]:
    rows = session.exec(select(CaseComment).where(CaseComment.case_id == case_id)).all()
    return [
        {"username": r.username, "body": r.body, "created_at": _iso(r.created_at)}
        for r in rows
    ]


def _dump_notes(session, case_id: int) -> list[dict]:
    rows = session.exec(select(CaseNote).where(CaseNote.case_id == case_id)).all()
    return [
        {"username": r.username, "kind": r.kind, "body": r.body, "created_at": _iso(r.created_at)}
        for r in rows
    ]


def _dump_watchlist(session, case_id: int) -> list[dict]:
    rows = session.exec(select(WatchlistTarget).where(WatchlistTarget.case_id == case_id)).all()
    return [
        {
            "query": r.query, "kind": r.kind, "notes": r.notes,
            "created_at": _iso(r.created_at), "last_checked": _iso(r.last_checked),
            "last_result_hash": r.last_result_hash,
            "has_alert": r.has_alert, "alert_message": r.alert_message,
        }
        for r in rows
    ]


def _dump_tracking(session, case_id: int) -> list[dict]:
    links = session.exec(select(TrackingLink).where(TrackingLink.case_id == case_id)).all()
    out = []
    for link in links:
        hits = session.exec(select(TrackingHit).where(TrackingHit.link_id == link.id)).all()
        out.append({
            "label": link.label, "decoy_mode": link.decoy_mode,
            "redirect_url": link.redirect_url, "notes": link.notes,
            "created_at": _iso(link.created_at),
            "hits": [
                {
                    "hit_type": h.hit_type, "ip": h.ip, "user_agent": h.user_agent,
                    "referrer": h.referrer, "country": h.country, "city": h.city,
                    "isp": h.isp, "lat": h.lat, "lon": h.lon, "screen": h.screen,
                    "timezone": h.timezone, "language": h.language, "platform": h.platform,
                    "browser": h.browser, "plugins": h.plugins, "gps_lat": h.gps_lat,
                    "gps_lon": h.gps_lon, "gps_accuracy": h.gps_accuracy,
                    "created_at": _iso(h.created_at),
                }
                for h in hits
            ],
        })
    return out


def build_backup_zip(case, password: str) -> bytes:
    """Return AES-256-encrypted zip bytes containing every piece of data
    scoped to this case. `case` is a Case row (only .id and .title are
    used, so a plain object with those attributes works too)."""
    with session_scope() as session:
        manifest = {
            "version": _MANIFEST_VERSION,
            "case_id": case.id,
            "case_title": case.title,
            "exported_at": _iso(datetime.datetime.utcnow()),
        }
        payload = {
            "manifest": manifest,
            "investigations": _dump_investigations(session, case.id),
            "comments": _dump_comments(session, case.id),
            "notes": _dump_notes(session, case.id),
            "watchlist": _dump_watchlist(session, case.id),
            "tracking_links": _dump_tracking(session, case.id),
        }

    buf = io.BytesIO()
    with pyzipper.AESZipFile(buf, "w", compression=pyzipper.ZIP_LZMA,
                              encryption=pyzipper.WZ_AES) as zf:
        zf.setpassword(password.encode("utf-8"))
        for name, data in payload.items():
            zf.writestr(f"{name}.json", json.dumps(data, indent=2))
    return buf.getvalue()


# ── Restore ──────────────────────────────────────────────────────────────────

def _open_backup(zip_bytes: bytes, password: str) -> dict:
    try:
        with pyzipper.AESZipFile(io.BytesIO(zip_bytes)) as zf:
            zf.setpassword(password.encode("utf-8"))
            names = set(zf.namelist())
            required = {"manifest.json", "investigations.json", "comments.json",
                        "notes.json", "watchlist.json", "tracking_links.json"}
            if not required.issubset(names):
                raise InvalidBackupError("This file isn't a recognized case backup.")
            return {name[:-5]: json.loads(zf.read(name)) for name in required}
    except RuntimeError as exc:
        # pyzipper raises a bare RuntimeError("Bad password for file ...")
        # on a wrong password — no dedicated exception type to catch.
        if "password" in str(exc).lower():
            raise WrongPasswordError("Incorrect password for this backup file.") from exc
        raise InvalidBackupError(f"Could not read this backup file: {exc}") from exc
    except (pyzipper.BadZipFile, json.JSONDecodeError, KeyError) as exc:
        raise InvalidBackupError(f"This doesn't look like a valid backup file: {exc}") from exc


def restore_backup_zip(case_id: int, zip_bytes: bytes, password: str) -> dict:
    """Decrypt and re-create every record from a backup into `case_id`,
    preserving each record's original timestamp — as if the case's data
    had never been deleted. Returns a summary of how many rows of each
    kind were restored. Raises WrongPasswordError or InvalidBackupError
    on failure; nothing is written to the database in that case."""
    data = _open_backup(zip_bytes, password)

    counts = {"investigations": 0, "comments": 0, "notes": 0,
              "watchlist": 0, "tracking_links": 0, "tracking_hits": 0}

    with session_scope() as session:
        for item in data["investigations"]:
            session.add(Investigation(
                kind=item["kind"], query=item["query"], result_json=item["result_json"],
                confidence=item.get("confidence") or "UNVERIFIED", tags=item.get("tags") or "",
                created_at=_parse_iso(item.get("created_at")) or datetime.datetime.utcnow(),
                updated_at=_parse_iso(item.get("updated_at")),
                case_id=case_id, user_id=None,
            ))
            counts["investigations"] += 1

        for item in data["comments"]:
            session.add(CaseComment(
                case_id=case_id, user_id=None, username=item.get("username") or "",
                body=item["body"],
                created_at=_parse_iso(item.get("created_at")) or datetime.datetime.utcnow(),
            ))
            counts["comments"] += 1

        for item in data["notes"]:
            session.add(CaseNote(
                case_id=case_id, user_id=None, username=item.get("username") or "",
                kind=item.get("kind") or "observation", body=item["body"],
                created_at=_parse_iso(item.get("created_at")) or datetime.datetime.utcnow(),
            ))
            counts["notes"] += 1

        for item in data["watchlist"]:
            session.add(WatchlistTarget(
                case_id=case_id, user_id=None, query=item["query"], kind=item["kind"],
                notes=item.get("notes") or "",
                created_at=_parse_iso(item.get("created_at")) or datetime.datetime.utcnow(),
                last_checked=_parse_iso(item.get("last_checked")),
                last_result_hash=item.get("last_result_hash") or "",
                has_alert=bool(item.get("has_alert")), alert_message=item.get("alert_message") or "",
            ))
            counts["watchlist"] += 1

        for link_item in data["tracking_links"]:
            # A fresh token, never the original — restoring a link
            # shouldn't silently resurrect a previously-shared public URL.
            link = TrackingLink(
                token=secrets.token_urlsafe(10), label=link_item["label"], case_id=case_id,
                user_id=None, decoy_mode=link_item.get("decoy_mode") or "404",
                redirect_url=link_item.get("redirect_url") or "", notes=link_item.get("notes") or "",
                created_at=_parse_iso(link_item.get("created_at")) or datetime.datetime.utcnow(),
            )
            session.add(link)
            session.flush()  # need link.id before inserting its hits
            counts["tracking_links"] += 1
            for h in link_item.get("hits", []):
                session.add(TrackingHit(
                    link_id=link.id, hit_type=h.get("hit_type") or "link",
                    ip=h.get("ip") or "", user_agent=h.get("user_agent") or "",
                    referrer=h.get("referrer") or "", country=h.get("country") or "",
                    city=h.get("city") or "", isp=h.get("isp") or "",
                    lat=h.get("lat"), lon=h.get("lon"), screen=h.get("screen") or "",
                    timezone=h.get("timezone") or "", language=h.get("language") or "",
                    platform=h.get("platform") or "", browser=h.get("browser") or "",
                    plugins=h.get("plugins") or "", gps_lat=h.get("gps_lat"),
                    gps_lon=h.get("gps_lon"), gps_accuracy=h.get("gps_accuracy"),
                    created_at=_parse_iso(h.get("created_at")) or datetime.datetime.utcnow(),
                ))
                counts["tracking_hits"] += 1

    return counts
