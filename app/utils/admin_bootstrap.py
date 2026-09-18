"""Shared logic for creating/resetting the admin account.

Used by both the root-level ``reset_admin.py`` script (git-clone workflow)
and the ``osint-tracker-reset-admin`` console script (pipx/pip install
workflow), so the two entry points can't drift out of sync.
"""
from argon2 import PasswordHasher
from app.db import init_db, get_session
from app.models.user import User
from sqlmodel import select

ph = PasswordHasher()


def reset_admin(password: str) -> str:
    """Create the admin user if absent, or reset its password if present.

    Args:
        password: The new plaintext admin password (validated by caller,
            but re-checked here since this is also a public API).

    Returns:
        A human-readable status message ("created" or "reset successfully").

    Raises:
        ValueError: If the password is shorter than 8 characters.
    """
    if len(password) < 8:
        raise ValueError("ADMIN_PASSWORD must be at least 8 characters long")

    init_db()

    with get_session() as session:
        stmt = select(User).where(User.username == "admin")
        admin = session.exec(stmt).first()

        if admin:
            admin.password_hash = ph.hash(password)
            session.add(admin)
            session.commit()
            return "reset successfully"

        admin = User(
            username="admin",
            password_hash=ph.hash(password),
            is_admin=True,
        )
        session.add(admin)
        session.commit()
        return "created successfully"
