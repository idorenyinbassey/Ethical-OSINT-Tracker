"""Shared pytest fixtures.

Sets up an isolated temp SQLite database and required environment BEFORE the
application package is imported, so the module-level engine in app.db binds to
the throwaway test database rather than the developer's dev.db.
"""
import os
import tempfile

# ---------------------------------------------------------------------------
# Environment must be configured before importing anything from `app`.
# ---------------------------------------------------------------------------
_DB_FD, _DB_PATH = tempfile.mkstemp(suffix=".db", prefix="osint_test_")
os.environ["DB_URL"] = f"sqlite:///{_DB_PATH}"
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("ADMIN_PASSWORD", "test-password-12345")

from cryptography.fernet import Fernet  # noqa: E402

os.environ.setdefault("API_KEYS_FERNET_KEY", Fernet.generate_key().decode())

import pytest  # noqa: E402
from argon2 import PasswordHasher  # noqa: E402

from app import create_app  # noqa: E402
from app.db import init_db  # noqa: E402
from app.repositories.user_repository import create_user, set_admin  # noqa: E402
from app.repositories.case_repository import create_case  # noqa: E402
from app.utils import rate_limiter  # noqa: E402

_ph = PasswordHasher()
_PASSWORD = "correct-horse-battery"


@pytest.fixture(scope="session")
def app():
    application = create_app()
    application.config["TESTING"] = True
    application.config["WTF_CSRF_ENABLED"] = False
    # NOTE: do NOT hold an app context open across the whole session. flask-login
    # caches the logged-in user on `g` (bound to the app context), so a lingering
    # context would leak authentication state between tests. init_db in a
    # short-lived context, then hand back the app with no context active.
    with application.app_context():
        init_db()
    return application


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """Each test starts with a clean rate-limit window."""
    rate_limiter._rate_store.clear()
    yield
    rate_limiter._rate_store.clear()


def _make_user(app, username, admin=False):
    with app.app_context():
        user = create_user(username, _ph.hash(_PASSWORD))
        if admin:
            set_admin(user.id, True)
        return user


@pytest.fixture()
def user_a(app):
    return _make_user(app, f"user_a_{os.urandom(4).hex()}")


@pytest.fixture()
def user_b(app):
    return _make_user(app, f"user_b_{os.urandom(4).hex()}")


@pytest.fixture()
def admin_user(app):
    return _make_user(app, f"admin_{os.urandom(4).hex()}", admin=True)


@pytest.fixture()
def case_of_a(app, user_a):
    with app.app_context():
        return create_case("Case A", "owned by A", owner_user_id=user_a.id)


def login(client, username, password=_PASSWORD):
    """Log a user in through the real /login route (CSRF disabled in tests)."""
    return client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=False,
    )


# Expose the shared password so individual tests can reference it.
PASSWORD = _PASSWORD
