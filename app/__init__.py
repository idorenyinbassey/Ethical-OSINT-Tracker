import os
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
            "API_KEYS_FERNET_KEY not set — API keys will be stored unencrypted. "
            "This is INSECURE for production. "
            "Generate a key with: python -c \"from cryptography.fernet import Fernet; "
            "print(Fernet.generate_key().decode())\" "
            "and set API_KEYS_FERNET_KEY environment variable.",
            stacklevel=2,
        )

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

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

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(investigation_bp)
    app.register_blueprint(cases_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(tracker_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(audit_bp)
    app.register_blueprint(admin_bp)

    # Public tracking endpoints have no session — exempt from CSRF
    csrf.exempt(land)
    csrf.exempt(pixel)
    csrf.exempt(collect_fingerprint)

    # Start background watchlist rescan scheduler
    from app.utils.scheduler import start_scheduler
    start_scheduler(app)

    @app.after_request
    def set_security_headers(response):
        """Add HTTP security headers to every response (Issue #17).

        The CSP intentionally allows the CDN/inline resources the UI already
        depends on (Tailwind CDN, unpkg for Leaflet/vis-network, OpenStreetMap
        tiles, DuckDuckGo favicons) while still constraining everything else to
        'self'. img-src allows https: so map tiles and remote favicons load.
        """
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com https://unpkg.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com https://unpkg.com; "
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
