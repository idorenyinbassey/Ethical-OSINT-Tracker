"""Headless-browser snapshots of the live /investigate/map and
/investigate/graph pages, for embedding into downloadable case reports.

Fully optional: if the `playwright` package or its browser binaries
aren't installed, capture is silently skipped and report generation
proceeds without the image — the same "optional dependency, degrade
gracefully" convention used for Pillow (image_client.PILLOW_AVAILABLE).

Renders against this process's own HTTP server (127.0.0.1:$FLASK_PORT)
using a Flask-Login session cookie forged in-process for the exporting
user — no stored credentials, no real login round-trip, no request ever
leaves the container.
"""
import logging
import os
import time

logger = logging.getLogger(__name__)

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

_SNAPSHOT_TIMEOUT_MS = 20_000
_POLL_INTERVAL_S = 0.5
_VIEWPORT = {"width": 1100, "height": 800}


def _internal_base_url() -> str:
    port = os.getenv("FLASK_PORT", "3000")
    return f"http://127.0.0.1:{port}"


def _forge_session_cookie(app, user_id: int) -> tuple[str, str]:
    """Build a valid Flask-Login session cookie for `user_id` without a
    real login — same serialization Flask's default session interface
    uses internally, so the resulting cookie is indistinguishable from
    one issued by a normal /login POST.
    """
    serializer = app.session_interface.get_signing_serializer(app)
    if serializer is None:
        raise RuntimeError("Flask app has no SECRET_KEY configured — cannot forge a session cookie")
    cookie_value = serializer.dumps({"_user_id": str(user_id), "_fresh": True})
    cookie_name = app.config.get("SESSION_COOKIE_NAME", "session")
    return cookie_name, cookie_value


def _launch_kwargs() -> dict:
    kwargs = {"headless": True, "args": ["--no-sandbox"]}
    override = os.getenv("PLAYWRIGHT_CHROMIUM_EXECUTABLE")
    if override:
        kwargs["executable_path"] = override
    return kwargs


def _capture_page_snapshot(app, user_id: int, path: str, ready_flag: str,
                            count_flag: str, selector: str) -> bytes | None:
    """Navigate to `path` as `user_id`, wait for the page's own `ready_flag`
    (set by map.html/graph.html once rendering settles), and screenshot
    `selector`. Returns None — never raises — if Playwright isn't
    available, the page has no data to show (`count_flag` is 0), or
    anything goes wrong.
    """
    if not PLAYWRIGHT_AVAILABLE:
        return None

    try:
        cookie_name, cookie_value = _forge_session_cookie(app, user_id)
        base_url = _internal_base_url()

        with sync_playwright() as p:
            browser = p.chromium.launch(**_launch_kwargs())
            try:
                context = browser.new_context(viewport=_VIEWPORT)
                context.add_cookies([{
                    "name": cookie_name, "value": cookie_value, "url": base_url,
                }])
                page = context.new_page()
                page.goto(f"{base_url}{path}", timeout=_SNAPSHOT_TIMEOUT_MS, wait_until="domcontentloaded")

                # Poll via plain evaluate() rather than wait_for_function():
                # the app's CSP has no 'unsafe-eval', and wait_for_function
                # injects a polling predicate that Chromium treats as eval,
                # which the CSP blocks. A one-shot evaluate() per poll is a
                # CDP-level call, not a page-executed script, so it isn't
                # subject to the page's own CSP.
                deadline = time.monotonic() + (_SNAPSHOT_TIMEOUT_MS / 1000)
                while time.monotonic() < deadline:
                    if page.evaluate(f"window.{ready_flag} === true"):
                        break
                    time.sleep(_POLL_INTERVAL_S)
                else:
                    return None

                count = page.evaluate(f"window.{count_flag}")
                if not count:
                    return None

                element = page.locator(selector)
                if element.count() == 0:
                    return None
                return element.screenshot()
            finally:
                browser.close()
    except Exception:
        logger.exception("Report snapshot capture failed for %s", path)
        return None


def capture_map_snapshot(app, user_id: int, case_id: int) -> bytes | None:
    """PNG screenshot of the case's geo-tagged findings on the location
    map, or None if unavailable/empty/failed."""
    return _capture_page_snapshot(
        app, user_id, f"/investigate/map?case_id={case_id}",
        ready_flag="__mapReady", count_flag="__mapMarkerCount", selector="#map",
    )


def capture_graph_snapshot(app, user_id: int, case_id: int) -> bytes | None:
    """PNG screenshot of the case's relationship graph, or None if
    unavailable/empty/failed."""
    return _capture_page_snapshot(
        app, user_id, f"/investigate/graph?case_id={case_id}",
        ready_flag="__graphReady", count_flag="__graphNodeCount", selector="#graph-container",
    )
