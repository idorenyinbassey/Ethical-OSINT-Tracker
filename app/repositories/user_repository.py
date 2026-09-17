from typing import Optional, List
from sqlmodel import select
from app.models.user import User
from app.repositories.base import session_scope


def get_by_id(user_id: int) -> Optional[User]:
    with session_scope(expire_on_commit=False) as session:
        user = session.get(User, user_id)
        if user:
            session.refresh(user)
        return user


def get_by_username(username: str) -> Optional[User]:
    with session_scope(expire_on_commit=False) as session:
        stmt = select(User).where(User.username == username)
        user = session.exec(stmt).first()
        if user:
            # Force load all attributes while session is active
            session.refresh(user)
        return user


def list_users() -> List[User]:
    """Get all users"""
    with session_scope(expire_on_commit=False) as session:
        stmt = select(User).order_by(User.username)
        users = list(session.exec(stmt))
        for user in users:
            session.expunge(user)
        return users


def set_admin(user_id: int, is_admin: bool) -> bool:
    with session_scope() as session:
        user = session.get(User, user_id)
        if not user:
            return False
        user.is_admin = is_admin
        session.add(user)
        return True


def set_active(user_id: int, is_active: bool) -> bool:
    with session_scope() as session:
        user = session.get(User, user_id)
        if not user:
            return False
        user.is_active = is_active
        session.add(user)
        return True


def delete_user(user_id: int) -> bool:
    with session_scope() as session:
        user = session.get(User, user_id)
        if not user:
            return False
        session.delete(user)
        return True


def update_password(user_id: int, new_password_hash: str) -> bool:
    with session_scope() as session:
        user = session.get(User, user_id)
        if not user:
            return False
        user.password_hash = new_password_hash
        session.add(user)
        return True


def create_user(username: str, password_hash: str) -> User:
    with session_scope(expire_on_commit=False) as session:
        user = User(username=username, password_hash=password_hash)
        session.add(user)
        session.flush()
        session.refresh(user)
        return user


# ── TOTP two-factor auth ────────────────────────────────────────────────────

def set_totp_secret(user_id: int, encrypted_secret: str | None) -> bool:
    """Store (or clear, with None) the user's Fernet-encrypted TOTP secret.
    Does not itself enable 2FA — see enable_totp."""
    with session_scope() as session:
        user = session.get(User, user_id)
        if not user:
            return False
        user.totp_secret = encrypted_secret
        session.add(user)
        return True


def enable_totp(user_id: int) -> bool:
    with session_scope() as session:
        user = session.get(User, user_id)
        if not user:
            return False
        user.totp_enabled = True
        session.add(user)
        return True


def disable_totp(user_id: int) -> bool:
    """Disable 2FA and wipe the secret + recovery codes."""
    with session_scope() as session:
        user = session.get(User, user_id)
        if not user:
            return False
        user.totp_enabled = False
        user.totp_secret = None
        user.totp_recovery_codes = ""
        session.add(user)
        return True


def set_recovery_codes(user_id: int, hashed_codes_json: str) -> bool:
    """Replace the stored (hashed) recovery codes — regenerating
    invalidates any codes not carried over into the new set."""
    with session_scope() as session:
        user = session.get(User, user_id)
        if not user:
            return False
        user.totp_recovery_codes = hashed_codes_json
        session.add(user)
        return True


def consume_recovery_code(user_id: int, code_hash: str) -> bool:
    """Remove one matching hashed recovery code (one-time use). Returns
    True if a match was found and consumed."""
    import json
    with session_scope() as session:
        user = session.get(User, user_id)
        if not user or not user.totp_recovery_codes:
            return False
        try:
            codes = json.loads(user.totp_recovery_codes)
        except Exception:
            return False
        if code_hash not in codes:
            return False
        codes.remove(code_hash)
        user.totp_recovery_codes = json.dumps(codes)
        session.add(user)
        return True
