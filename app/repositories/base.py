from contextlib import contextmanager
from app.db import get_session


@contextmanager
def session_scope(expire_on_commit=True):
    session = get_session()
    session.expire_on_commit = expire_on_commit
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
