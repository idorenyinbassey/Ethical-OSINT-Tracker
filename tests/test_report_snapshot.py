"""app.services.report_snapshot — headless-browser map/graph screenshots
for report embedding. Fully mocked (no real browser): verifies session
cookie forging round-trips through Flask's own session interface, and
that capture degrades to None (never raises) whenever Playwright is
unavailable, there's nothing to show, or anything goes wrong."""
from unittest.mock import patch, MagicMock
from app.services import report_snapshot


def test_forge_session_cookie_roundtrips_through_flask(app):
    """The forged cookie must be indistinguishable from one Flask itself
    would issue on a real login — i.e. Flask's own session interface must
    be able to unsign and read it back."""
    cookie_name, cookie_value = report_snapshot._forge_session_cookie(app, user_id=42)
    assert cookie_name == app.config.get("SESSION_COOKIE_NAME", "session")

    serializer = app.session_interface.get_signing_serializer(app)
    decoded = serializer.loads(cookie_value)
    assert decoded["_user_id"] == "42"
    assert decoded["_fresh"] is True


def test_internal_base_url_uses_flask_port_env(monkeypatch):
    monkeypatch.setenv("FLASK_PORT", "4321")
    assert report_snapshot._internal_base_url() == "http://127.0.0.1:4321"


def test_internal_base_url_defaults_to_3000(monkeypatch):
    monkeypatch.delenv("FLASK_PORT", raising=False)
    assert report_snapshot._internal_base_url() == "http://127.0.0.1:3000"


def test_capture_returns_none_when_playwright_unavailable(app):
    with patch.object(report_snapshot, "PLAYWRIGHT_AVAILABLE", False):
        assert report_snapshot.capture_map_snapshot(app, user_id=1, case_id=1) is None
        assert report_snapshot.capture_graph_snapshot(app, user_id=1, case_id=1) is None


def test_capture_returns_none_on_any_exception(app):
    with patch.object(report_snapshot, "PLAYWRIGHT_AVAILABLE", True), \
         patch.object(report_snapshot, "sync_playwright", side_effect=RuntimeError("boom")):
        result = report_snapshot.capture_map_snapshot(app, user_id=1, case_id=1)
    assert result is None


class _FakePage:
    def __init__(self, ready_value, count_value, element_count=1, screenshot_bytes=b"PNGDATA"):
        self._ready_value = ready_value
        self._count_value = count_value
        self._element_count = element_count
        self._screenshot_bytes = screenshot_bytes
        self.evaluate_calls = []

    def goto(self, *a, **kw):
        pass

    def evaluate(self, script):
        self.evaluate_calls.append(script)
        if "Ready" in script:
            return self._ready_value
        return self._count_value

    def locator(self, selector):
        page = self

        class _Locator:
            def count(self_inner):
                return page._element_count

            def screenshot(self_inner):
                return page._screenshot_bytes

        return _Locator()


class _FakeContext:
    def __init__(self, page):
        self._page = page
        self.cookies_added = None

    def add_cookies(self, cookies):
        self.cookies_added = cookies

    def new_page(self):
        return self._page


class _FakeBrowser:
    def __init__(self, page):
        self._page = page
        self.closed = False

    def new_context(self, **kw):
        return _FakeContext(self._page)

    def close(self):
        self.closed = True


class _FakeChromium:
    def __init__(self, page):
        self._page = page

    def launch(self, **kw):
        return _FakeBrowser(self._page)


class _FakePlaywrightCM:
    def __init__(self, page):
        self._page = page

    def __enter__(self):
        return MagicMock(chromium=_FakeChromium(self._page))

    def __exit__(self, *exc):
        return False


def test_capture_returns_none_when_ready_but_zero_count(app):
    page = _FakePage(ready_value=True, count_value=0)
    with patch.object(report_snapshot, "PLAYWRIGHT_AVAILABLE", True), \
         patch.object(report_snapshot, "sync_playwright", return_value=_FakePlaywrightCM(page)):
        result = report_snapshot.capture_map_snapshot(app, user_id=1, case_id=1)
    assert result is None


def test_capture_returns_screenshot_bytes_when_ready_and_has_data(app):
    page = _FakePage(ready_value=True, count_value=3, screenshot_bytes=b"\x89PNGfakepng")
    with patch.object(report_snapshot, "PLAYWRIGHT_AVAILABLE", True), \
         patch.object(report_snapshot, "sync_playwright", return_value=_FakePlaywrightCM(page)), \
         patch.object(report_snapshot, "_SNAPSHOT_TIMEOUT_MS", 500), \
         patch.object(report_snapshot, "_POLL_INTERVAL_S", 0.01):
        result = report_snapshot.capture_map_snapshot(app, user_id=7, case_id=3)
    assert result == b"\x89PNGfakepng"


def test_capture_returns_none_if_never_becomes_ready(app):
    page = _FakePage(ready_value=False, count_value=5)
    with patch.object(report_snapshot, "PLAYWRIGHT_AVAILABLE", True), \
         patch.object(report_snapshot, "sync_playwright", return_value=_FakePlaywrightCM(page)), \
         patch.object(report_snapshot, "_SNAPSHOT_TIMEOUT_MS", 50), \
         patch.object(report_snapshot, "_POLL_INTERVAL_S", 0.01):
        result = report_snapshot.capture_map_snapshot(app, user_id=1, case_id=1)
    assert result is None


def test_capture_graph_snapshot_uses_graph_ready_flag(app):
    page = _FakePage(ready_value=True, count_value=2, screenshot_bytes=b"GRAPHPNG")
    with patch.object(report_snapshot, "PLAYWRIGHT_AVAILABLE", True), \
         patch.object(report_snapshot, "sync_playwright", return_value=_FakePlaywrightCM(page)), \
         patch.object(report_snapshot, "_SNAPSHOT_TIMEOUT_MS", 500), \
         patch.object(report_snapshot, "_POLL_INTERVAL_S", 0.01):
        result = report_snapshot.capture_graph_snapshot(app, user_id=1, case_id=1)
    assert result == b"GRAPHPNG"
    assert any("__graphReady" in call for call in page.evaluate_calls)
