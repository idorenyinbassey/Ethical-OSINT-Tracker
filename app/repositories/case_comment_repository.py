from typing import List
from sqlmodel import select
from app.models.case_comment import CaseComment
from app.repositories.base import session_scope


def add_comment(case_id: int, user_id: int | None, username: str, body: str) -> CaseComment:
    with session_scope() as session:
        c = CaseComment(case_id=case_id, user_id=user_id, username=username, body=body)
        session.add(c)
        session.flush()
        return CaseComment(
            id=c.id, case_id=c.case_id, user_id=c.user_id,
            username=c.username, body=c.body, created_at=c.created_at,
        )


def list_comments(case_id: int) -> List[CaseComment]:
    with session_scope() as session:
        stmt = select(CaseComment).where(CaseComment.case_id == case_id).order_by(CaseComment.created_at)
        rows = session.exec(stmt).all()
        return [CaseComment(id=r.id, case_id=r.case_id, user_id=r.user_id,
                            username=r.username, body=r.body, created_at=r.created_at)
                for r in rows]
