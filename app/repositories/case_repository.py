from typing import List, Optional
from sqlmodel import select
from app.models.case import Case
from app.repositories.base import session_scope


def list_cases() -> List[Case]:
    with session_scope() as session:
        stmt = select(Case).order_by(Case.created_at.desc())
        results = session.exec(stmt).all()
        # Eagerly load all attributes before session closes
        return [Case(
            id=c.id,
            title=c.title,
            description=c.description,
            status=c.status,
            priority=c.priority,
            owner_user_id=c.owner_user_id,
            created_at=c.created_at
        ) for c in results]


def get_case(case_id: int) -> Optional[Case]:
    with session_scope() as session:
        stmt = select(Case).where(Case.id == case_id)
        return session.exec(stmt).first()


def create_case(title: str, description: str, owner_user_id: int | None, priority: str = "medium") -> Case:
    with session_scope() as session:
        case = Case(title=title, description=description, owner_user_id=owner_user_id, priority=priority)
        session.add(case)
        session.flush()
        session.refresh(case)
        # Return a plain detached instance with attributes populated to avoid
        # DetachedInstanceError when accessed outside the session context.
        return Case(
            id=case.id,
            title=case.title,
            description=case.description,
            status=case.status,
            priority=case.priority,
            owner_user_id=case.owner_user_id,
            created_at=case.created_at,
            updated_at=case.updated_at,
        )


def update_case(case_id: int, **fields) -> Optional[Case]:
    with session_scope() as session:
        stmt = select(Case).where(Case.id == case_id)
        case = session.exec(stmt).first()
        if not case:
            return None
        for k, v in fields.items():
            if hasattr(case, k):
                setattr(case, k, v)
        session.add(case)
        session.flush()
        session.refresh(case)
        return case


def delete_case(case_id: int) -> bool:
    with session_scope() as session:
        stmt = select(Case).where(Case.id == case_id)
        case = session.exec(stmt).first()
        if case:
            session.delete(case)
            return True
        return False
