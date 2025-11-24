from typing import List, Optional
from sqlmodel import select
from app.models.intelligence_report import IntelligenceReport
from app.repositories.base import session_scope


def list_reports() -> List[IntelligenceReport]:
    with session_scope() as session:
        stmt = select(IntelligenceReport).order_by(IntelligenceReport.created_at.desc())
        return list(session.exec(stmt))


def create_report(title: str, summary: str, indicators: str, author_user_id: int | None, related_case_id: int | None = None) -> IntelligenceReport:
    with session_scope() as session:
        rpt = IntelligenceReport(title=title, summary=summary, indicators=indicators, author_user_id=author_user_id, related_case_id=related_case_id)
        session.add(rpt)
        session.flush()
        session.refresh(rpt)
        return rpt


def delete_report(report_id: int) -> bool:
    with session_scope() as session:
        stmt = select(IntelligenceReport).where(IntelligenceReport.id == report_id)
        rpt = session.exec(stmt).first()
        if rpt:
            session.delete(rpt)
            return True
        return False
