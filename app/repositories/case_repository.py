from typing import List, Optional
from sqlmodel import select
from app.models.case import Case
from app.models.team import TeamMember
from app.repositories.base import session_scope


def list_cases(owner_user_id: int | None = None) -> List[Case]:
    with session_scope() as session:
        stmt = select(Case).order_by(Case.created_at.desc())
        if owner_user_id is not None:
            stmt = stmt.where(Case.owner_user_id == owner_user_id)
        results = session.exec(stmt).all()
        # Eagerly load all attributes before session closes
        return [Case(
            id=c.id,
            title=c.title,
            description=c.description,
            status=c.status,
            priority=c.priority,
            owner_user_id=c.owner_user_id,
            team_id=c.team_id,
            created_at=c.created_at
        ) for c in results]


def list_cases_for_user(user_id: int) -> List[Case]:
    """Cases owned by `user_id`, plus cases shared with any team they
    belong to. Deliberately a separate function from `list_cases` (rather
    than a signature change) so the ~25 existing call sites that already
    pass owner_user_id=... for strict single-owner scoping are unaffected.
    """
    with session_scope() as session:
        team_ids = [
            m.team_id for m in session.exec(
                select(TeamMember).where(TeamMember.user_id == user_id)
            ).all()
        ]
        stmt = select(Case).order_by(Case.created_at.desc())
        if team_ids:
            stmt = stmt.where(
                (Case.owner_user_id == user_id) | (Case.team_id.in_(team_ids))
            )
        else:
            stmt = stmt.where(Case.owner_user_id == user_id)
        results = session.exec(stmt).all()
        return [Case(
            id=c.id,
            title=c.title,
            description=c.description,
            status=c.status,
            priority=c.priority,
            owner_user_id=c.owner_user_id,
            team_id=c.team_id,
            created_at=c.created_at,
        ) for c in results]


def get_case(case_id: int) -> Optional[Case]:
    with session_scope() as session:
        stmt = select(Case).where(Case.id == case_id)
        c = session.exec(stmt).first()
        if c is None:
            return None
        return Case(
            id=c.id,
            title=c.title,
            description=c.description,
            status=c.status,
            priority=c.priority,
            owner_user_id=c.owner_user_id,
            team_id=c.team_id,
            created_at=c.created_at,
            updated_at=getattr(c, "updated_at", None),
        )


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
            team_id=case.team_id,
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
        return Case(
            id=case.id,
            title=case.title,
            description=case.description,
            status=case.status,
            priority=case.priority,
            owner_user_id=case.owner_user_id,
            team_id=case.team_id,
            created_at=case.created_at,
            updated_at=getattr(case, "updated_at", None),
        )


def delete_case(case_id: int) -> bool:
    with session_scope() as session:
        stmt = select(Case).where(Case.id == case_id)
        case = session.exec(stmt).first()
        if case:
            session.delete(case)
            return True
        return False
