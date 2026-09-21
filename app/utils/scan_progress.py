"""In-memory "N of M checked" progress tracking for long-running fan-out
scans (Social Search's ~600+ site checks, Company Registry's 11-jurisdiction
search) — a purely additive side channel alongside the existing synchronous
request/response flow, not a replacement for it.

The browser generates a random token per submission and polls
GET /investigate/scan-progress/<token> while the same synchronous POST is
in flight (fired via fetch() rather than a native form submit, so the two
requests run concurrently). A token is unguessable and only ever exposes a
"checked"/"total" count, never actual result content, so no per-user
ownership check is needed here — unlike the report-export job store in
app/routes/cases.py, which does hold real, downloadable content.
"""
import time

_TTL_SECONDS = 300  # stale entries are pruned lazily on next read/write
_progress: dict[str, dict] = {}


def make_callback(token: str | None):
    """Return a progress_cb(checked, total) bound to this token, or None if
    no token was supplied (the caller just skips reporting progress)."""
    if not token:
        return None

    _prune()
    _progress[token] = {"checked": 0, "total": 0, "ts": time.time()}

    def _cb(checked: int, total: int) -> None:
        _progress[token] = {"checked": checked, "total": total, "ts": time.time()}

    return _cb


def get_progress(token: str) -> dict:
    _prune()
    entry = _progress.get(token)
    return {"checked": entry["checked"], "total": entry["total"]} if entry else {"checked": 0, "total": 0}


def _prune() -> None:
    cutoff = time.time() - _TTL_SECONDS
    for key in [k for k, v in _progress.items() if v["ts"] < cutoff]:
        _progress.pop(key, None)
