from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from sqlmodel import select, or_

search_bp = Blueprint("search", __name__)


@search_bp.route("/search")
@login_required
def results():
    q = request.args.get("q", "").strip()
    if not q:
        return render_template("search/results.html", q="", investigations=[], cases=[], notes=[], total=0)

    from app.db import get_session
    from app.models.investigation import Investigation
    from app.models.case import Case
    from app.models.case_note import CaseNote

    pat = f"%{q}%"
    investigations, cases, notes = [], [], []

    with get_session() as session:
        inv_rows = session.exec(
            select(Investigation).where(
                or_(Investigation.query.like(pat),
                    Investigation.result_json.like(pat),
                    Investigation.kind.like(pat))
            ).order_by(Investigation.created_at.desc()).limit(50)
        ).all()
        investigations = [Investigation(
            id=r.id, kind=r.kind, query=r.query,
            result_json=r.result_json, confidence=r.confidence,
            case_id=r.case_id, created_at=r.created_at,
        ) for r in inv_rows]

        case_rows = session.exec(
            select(Case).where(
                or_(Case.title.like(pat), Case.description.like(pat))
            ).order_by(Case.created_at.desc()).limit(20)
        ).all()
        cases = [Case(id=r.id, title=r.title, description=r.description,
                      status=r.status, created_at=r.created_at) for r in case_rows]

        note_rows = session.exec(
            select(CaseNote).where(CaseNote.body.like(pat))
            .order_by(CaseNote.created_at.desc()).limit(20)
        ).all()
        notes = [CaseNote(id=r.id, case_id=r.case_id, username=r.username,
                          kind=r.kind, body=r.body, created_at=r.created_at) for r in note_rows]

    total = len(investigations) + len(cases) + len(notes)
    return render_template("search/results.html", q=q,
                           investigations=investigations, cases=cases,
                           notes=notes, total=total)
