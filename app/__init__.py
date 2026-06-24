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

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(investigation_bp)
    app.register_blueprint(cases_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(tracker_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(audit_bp)

    # Public tracking endpoints have no session — exempt from CSRF
    csrf.exempt(land)
    csrf.exempt(pixel)
    csrf.exempt(collect_fingerprint)

    # Start background watchlist rescan scheduler
    from app.utils.scheduler import start_scheduler
    start_scheduler(app)

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
