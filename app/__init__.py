import os
from flask import Flask
from flask_login import LoginManager
from app.config import Config
from app.db import init_db

login_manager = LoginManager()


def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(Config)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access this page."

    init_db()

    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.investigation import investigation_bp
    from app.routes.cases import cases_bp
    from app.routes.settings import settings_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(investigation_bp)
    app.register_blueprint(cases_bp)
    app.register_blueprint(settings_bp)

    return app


@login_manager.user_loader
def load_user(user_id):
    from app.repositories.user_repository import get_by_id
    return get_by_id(int(user_id))
