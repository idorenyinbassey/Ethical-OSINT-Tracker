from typing import List, Optional
from sqlmodel import select
from app.models.case import Case
from app.models.team import TeamMember
from app.models.investigation import Investigation
from app.models.case_comment import CaseComment
from app.models.case_note import CaseNote
from app.models.watchlist import WatchlistTarget
from app.models.tracking_link import TrackingLink
from app.models.tracking_hit import TrackingHit
from app.models.intelligence_report import IntelligenceReport
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
    """Delete a case and everything scoped to it, in one transaction.

    SQLite foreign-key enforcement is never turned on for this app (see
    app/db.py) and no ORM relationship()/cascade is declared on Case or its
    children, so an orphan-free delete has to be explicit application code
    rather than a DB-level cascade. Order matters: child-of-child rows
    (TrackingHit) go before their parent (TrackingLink).
    """
    with session_scope() as session:
        stmt = select(Case).where(Case.id == case_id)
        case = session.exec(stmt).first()
        if not case:
            return False

        for inv in session.exec(select(Investigation).where(Investigation.case_id == case_id)).all():
            session.delete(inv)
        for comment in session.exec(select(CaseComment).where(CaseComment.case_id == case_id)).all():
            session.delete(comment)
        for note in session.exec(select(CaseNote).where(CaseNote.case_id == case_id)).all():
            session.delete(note)
        for target in session.exec(select(WatchlistTarget).where(WatchlistTarget.case_id == case_id)).all():
            session.delete(target)

        links = session.exec(select(TrackingLink).where(TrackingLink.case_id == case_id)).all()
        for link in links:
            for hit in session.exec(select(TrackingHit).where(TrackingHit.link_id == link.id)).all():
                session.delete(hit)
            session.delete(link)

        # related_case_id has no real FK constraint declared at all (see the
        # model) — a finished report is more of a keepable export artifact
        # than working case data, so it's unlinked rather than deleted.
        for report in session.exec(select(IntelligenceReport).where(IntelligenceReport.related_case_id == case_id)).all():
            report.related_case_id = None
            session.add(report)

        session.delete(case)
        return True
