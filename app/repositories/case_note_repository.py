from typing import List
from sqlmodel import select
from app.models.case_note import CaseNote
from app.repositories.base import session_scope


def _detach(n: CaseNote) -> CaseNote:
    return CaseNote(
        id=n.id, case_id=n.case_id, user_id=n.user_id,
        username=n.username, kind=n.kind, body=n.body, created_at=n.created_at,
    )


def add_note(case_id: int, user_id: int | None, username: str, kind: str, body: str) -> CaseNote:
    with session_scope() as session:
        note = CaseNote(case_id=case_id, user_id=user_id, username=username, kind=kind, body=body)
        session.add(note)
        session.flush()
        return _detach(note)


def list_notes(case_id: int) -> List[CaseNote]:
    with session_scope() as session:
        results = session.exec(
            select(CaseNote)
            .where(CaseNote.case_id == case_id)
            .order_by(CaseNote.created_at.asc())
        ).all()
        return [_detach(n) for n in results]


def delete_note(note_id: int, user_id: int | None) -> bool:
    with session_scope() as session:
        note = session.get(CaseNote, note_id)
        if not note:
            return False
        if user_id and note.user_id and note.user_id != user_id:
            return False
        session.delete(note)
        return True
