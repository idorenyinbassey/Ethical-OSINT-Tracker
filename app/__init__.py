import ipaddress
import json
import os
import re
from flask import Flask
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from app.config import Config
from app.db import init_db

login_manager = LoginManager()
csrf = CSRFProtect()


def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(Config)

    # Check for required encryption key for API key storage
    if not app.config.get("API_KEYS_FERNET_KEY"):
        import warnings
        warnings.warn(
            "API_KEYS_FERNET_KEY not set — saving an API key in Settings will fail "
            "until this is configured (it stores unencrypted only in the unrelated "
            "case where the 'cryptography' library itself fails to load). "
            "Generate a key with: python -c \"from cryptography.fernet import Fernet; "
            "print(Fernet.generate_key().decode())\" and set API_KEYS_FERNET_KEY. "
            "start.sh / install_termux.sh generate and persist this for you automatically.",
            stacklevel=2,
        )

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # Trust X-Forwarded-* headers only when explicitly told to — needed
    # for Link Tracker's generated URLs (and anything else built from
    # request.host_url/url_for) to come out correct behind a reverse
    # proxy or tunnel (ngrok, Cloudflare Tunnel, nginx). Off by default:
    # blindly trusting these headers with no proxy in front would let a
    # direct client spoof its own apparent IP/scheme.
    if os.getenv("TRUST_PROXY_HEADERS", "0") == "1":
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access this page."

    csrf.init_app(app)

    init_db()

    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.investigation import investigation_bp
    from app.routes.cases import cases_bp
    from app.routes.settings import settings_bp
    from app.routes.tracker import tracker_bp, land, pixel, collect_fingerprint
    from app.routes.search import search_bp
    from app.routes.audit import audit_bp
    from app.routes.admin import admin_bp
    from app.routes.teams import teams_bp
    from app.routes.api_v1 import api_v1_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(investigation_bp)
    app.register_blueprint(cases_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(tracker_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(audit_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(teams_bp)
    app.register_blueprint(api_v1_bp)

    # Public tracking endpoints have no session — exempt from CSRF
    csrf.exempt(land)
    csrf.exempt(pixel)
    csrf.exempt(collect_fingerprint)
    # The whole /api/v1 surface is stateless (API-key auth, no cookies) —
    # exempt the entire blueprint rather than each view individually.
    csrf.exempt(api_v1_bp)

    # Start background watchlist rescan scheduler
    from app.utils.scheduler import start_scheduler
    start_scheduler(app)

    @app.after_request
    def set_security_headers(response):
        """Add HTTP security headers to every response (Issue #17).

        The CSP intentionally allows the CDN/inline resources the UI already
        depends on (Tailwind CDN, OpenStreetMap tiles, DuckDuckGo favicons)
        while still constraining everything else to 'self'. Leaflet and
        vis-network are vendored locally (app/static/vendor/) rather than
        loaded from unpkg, both so the map/graph still work in
        network-restricted deployments and so the headless report-snapshot
        renderer (app/services/report_snapshot.py) doesn't need outbound
        internet access just to draw the page. img-src allows https: so
        map tiles and remote favicons load.
        """
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self' https://cdn.tailwindcss.com; "
            "base-uri 'self'; "
            "form-action 'self'; "
            "frame-ancestors 'none'",
        )
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy", "geolocation=(), microphone=(), camera=()"
        )
        return response

    _IMAGE_FIELD_NAME_HINTS = (
        "avatar", "photo", "picture", "thumbnail", "thumb", "image", "img",
        "logo", "icon", "profile_pic",
    )

    def _is_image_value(value, field_name: str = "") -> bool:
        """True for a string that looks like an image, so the scan viewer
        can render an actual thumbnail instead of just showing raw text.

        Two ways in: a data: URI or a URL ending in a common image
        extension is always trusted. Beyond that, many real APIs (GitHub,
        Gravatar) serve avatars from extensionless URLs — those are only
        trusted when the field's own name hints it's an image (avatar,
        photo, thumbnail, ...), since a wrong guess there just means an
        extra thumbnail attempt, never a lost Copy button or hidden data.

        Either way, an http:// (non-TLS) URL is never trusted as an image:
        the CSP below only allows 'self', data:, and https: for img-src, so
        the browser would silently block the request and render a broken
        image icon instead of the raw text this value would otherwise show.
        """
        if not isinstance(value, str) or not value:
            return False
        if value.startswith("data:image/"):
            return True
        if not value.startswith(("https://", "data:")):
            return False
        lowered = value.split("?", 1)[0].lower()
        if lowered.endswith((".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg")):
            return True
        if field_name and any(hint in field_name.lower() for hint in _IMAGE_FIELD_NAME_HINTS):
            return True
        return False

    def _is_verbose_value(value) -> bool:
        """True for a value that's bulky/low-signal-density (a dict with
        many fields, or a list of several dicts/lists) — vs. a short list
        of plain values like username guesses, which is always shown
        immediately regardless of length. Used by the scan viewer to
        collapse verbose sections (e.g. a dozen reference links) by
        default, so a few high-signal fields aren't buried under them."""
        if isinstance(value, dict):
            return len(value) > 6
        if isinstance(value, (list, tuple)):
            if not value:
                return False
            first = value[0]
            if isinstance(first, (dict, list, tuple)):
                return len(value) > 3
            return False
        return False

    def _from_json(value):
        """Parse a stored result_json string for direct display in a
        template. Returns None on empty/malformed input rather than
        raising, matching this codebase's established
        graceful-degradation convention (e.g. investigation_view's own
        parse_error handling) — a corrupted old row shouldn't break the
        whole page it's listed on."""
        if not value:
            return None
        try:
            return json.loads(value)
        except (ValueError, TypeError):
            return None

    _EMAIL_FULL_RE = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*\.[a-zA-Z]{2,}$")
    # Last label must be letters-only (a real TLD is never purely numeric),
    # which also naturally excludes malformed/non-IPv4 dotted-number
    # strings like "123.456.789.0" from being misread as a domain.
    _DOMAIN_FULL_RE = re.compile(
        r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$"
    )
    _PHONE_FULL_RE = re.compile(r"^\+?[0-9][0-9\s\-()]{5,17}[0-9]$")

    def _investigate_tool_for(value, field_name: str = ""):
        """If `value` looks like an email, IP, domain, or phone number,
        return (endpoint, label) for the tool that investigates it — lets
        the scan viewer / tool history offer an "Investigate with X ->"
        link next to that value, so a value discovered in one result can
        lead straight into a follow-up scan with another tool ("one
        investigation leading to another"). Returns None when nothing
        recognized matches, which is the common case for most values
        (a display name, a status code, a boolean, ...).

        Deliberately conservative — a missed pivot just means one fewer
        convenience link, whereas a wrong one sends the user to the wrong
        tool with a nonsense prefilled query. Phone detection in
        particular requires either visible phone punctuation (+, -, (),
        a space) or an explicit "phone"-hinting field name for a bare
        digit string, mirroring is_image_value's field-name-hint
        tie-breaker convention above.
        """
        if not isinstance(value, str) or not value:
            return None
        v = value.strip()
        if _EMAIL_FULL_RE.match(v):
            return ("investigation.email", "Email Analysis")
        try:
            ipaddress.ip_address(v)
            return ("investigation.ip", "IP Lookup")
        except ValueError:
            pass
        if _DOMAIN_FULL_RE.match(v):
            return ("investigation.domain", "Domain WHOIS")
        digits = re.sub(r"\D", "", v)
        if 7 <= len(digits) <= 15 and _PHONE_FULL_RE.match(v):
            has_punctuation = any(ch in v for ch in "+-() ")
            if has_punctuation or (field_name and "phone" in field_name.lower()):
                return ("investigation.phone", "Phone Lookup")
        return None

    app.jinja_env.filters["is_image_value"] = _is_image_value
    app.jinja_env.filters["is_verbose_value"] = _is_verbose_value
    app.jinja_env.filters["from_json"] = _from_json
    app.jinja_env.filters["investigate_tool_for"] = _investigate_tool_for

    @app.context_processor
    def inject_active_case():
        from flask_login import current_user
        from flask import session
        active_case = None
        case_investigations = []
        if current_user.is_authenticated:
            cid = session.get('active_case_id')
            if cid:
                from app.repositories.case_repository import get_case
                from app.repositories.investigation_repository import list_by_case
                active_case = get_case(cid)
                if active_case:
                    case_investigations = list_by_case(cid)
        return dict(active_case=active_case, case_investigations=case_investigations)

    return app


@login_manager.user_loader
def load_user(user_id):
    from app.repositories.user_repository import get_by_id
    return get_by_id(int(user_id))
