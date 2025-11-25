from typing import Optional, List
from sqlmodel import select
from app.models.user import User
from app.repositories.base import session_scope


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


def create_user(username: str, password_hash: str) -> User:
    with session_scope(expire_on_commit=False) as session:
        user = User(username=username, password_hash=password_hash)
        session.add(user)
        session.flush()
        session.refresh(user)
        return user
