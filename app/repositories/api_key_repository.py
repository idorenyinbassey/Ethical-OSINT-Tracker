import hashlib
import secrets
import datetime
from typing import List, Optional
from sqlmodel import select
from app.models.api_key import ApiKey
from app.repositories.base import session_scope

_KEY_PREFIX = "osint_"


def _hash(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


def create_api_key(user_id: int, label: str = "") -> tuple[ApiKey, str]:
    """Create a new key for `user_id`. Returns (ApiKey row, raw key) — the
    raw key is never stored and is only available from this return value;
    show it to the user once and never again."""
    raw_key = _KEY_PREFIX + secrets.token_urlsafe(32)
    with session_scope(expire_on_commit=False) as session:
        key = ApiKey(user_id=user_id, key_hash=_hash(raw_key), label=label)
        session.add(key)
        session.flush()
        session.refresh(key)
        session.expunge(key)
        return key, raw_key


def list_active_keys(user_id: int) -> List[ApiKey]:
    with session_scope(expire_on_commit=False) as session:
        stmt = select(ApiKey).where(
            ApiKey.user_id == user_id, ApiKey.revoked == False,  # noqa: E712
        ).order_by(ApiKey.created_at.desc())
        keys = list(session.exec(stmt))
        for k in keys:
            session.expunge(k)
        return keys


def get_by_key_hash(key_hash: str) -> Optional[ApiKey]:
    with session_scope(expire_on_commit=False) as session:
        stmt = select(ApiKey).where(ApiKey.key_hash == key_hash)
        key = session.exec(stmt).first()
        if key:
            session.expunge(key)
        return key


def get_by_raw_key(raw_key: str) -> Optional[ApiKey]:
    return get_by_key_hash(_hash(raw_key))


def revoke_key(key_id: int, user_id: int) -> bool:
    """Revoke a key — only its owner may revoke it."""
    with session_scope() as session:
        key = session.get(ApiKey, key_id)
        if not key or key.user_id != user_id:
            return False
        key.revoked = True
        session.add(key)
        return True


def touch_last_used(key_id: int) -> None:
    with session_scope() as session:
        key = session.get(ApiKey, key_id)
        if key:
            key.last_used_at = datetime.datetime.utcnow()
            session.add(key)
