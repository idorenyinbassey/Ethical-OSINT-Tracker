"""app.utils.admin_bootstrap — shared create/reset logic behind reset_admin.py
and the `osint-tracker-reset-admin` console script (pipx/pip install path)."""
import pytest
from argon2 import PasswordHasher
from app.utils.admin_bootstrap import reset_admin
from app.repositories.user_repository import get_by_username, delete_user

ph = PasswordHasher()


def test_reset_admin_rejects_short_password(app):
    with app.app_context():
        with pytest.raises(ValueError):
            reset_admin("short")


def test_reset_admin_creates_when_absent(app):
    with app.app_context():
        existing = get_by_username("admin")
        if existing:
            delete_user(existing.id)

        status = reset_admin("brand-new-password")
        assert status == "created successfully"

        admin = get_by_username("admin")
        assert admin is not None
        assert admin.is_admin is True
        ph.verify(admin.password_hash, "brand-new-password")  # raises on mismatch


def test_reset_admin_resets_when_present(app):
    with app.app_context():
        status = reset_admin("another-new-password")
        assert status == "reset successfully"

        admin = get_by_username("admin")
        assert admin is not None
        ph.verify(admin.password_hash, "another-new-password")
