"""app.repositories.case_repository.delete_case() — deleting a case must
also delete everything scoped to it (investigations, comments, notes,
watchlist targets, tracking links + their hits), so a deleted case leaves
no orphaned rows behind that would otherwise keep showing up on the
map/graph. SQLite foreign-key enforcement is never turned on for this app
and no ORM cascade is declared, so this has to be exercised end to end
against the real repository functions rather than assumed from a
declared relationship()."""
import json

from app.repositories.case_repository import create_case, delete_case, get_case


def _seed_full_case(app, user_id):
    """Create a case with one row in every case-scoped table, and return
    (case, ids) so tests can assert each is gone after delete."""
    from app.repositories.investigation_repository import create_investigation
    from app.models.case_comment import CaseComment
    from app.models.case_note import CaseNote
    from app.models.watchlist import WatchlistTarget
    from app.models.tracking_link import TrackingLink
    from app.models.tracking_hit import TrackingHit
    from app.models.intelligence_report import IntelligenceReport
    from app.repositories.base import session_scope

    with app.app_context():
        case = create_case("Full Case", "has one of everything", owner_user_id=user_id)

        inv = create_investigation(
            kind="ip", query="8.8.8.8",
            result_json=json.dumps({"ip": "8.8.8.8", "geo": {"lat": 37.4, "lon": -122.08}}),
            user_id=user_id, case_id=case.id,
        )

        with session_scope() as session:
            comment = CaseComment(case_id=case.id, user_id=user_id, body="a comment")
            session.add(comment)
            note = CaseNote(case_id=case.id, user_id=user_id, body="a note")
            session.add(note)
            target = WatchlistTarget(case_id=case.id, user_id=user_id, query="8.8.8.8", kind="ip")
            session.add(target)
            link = TrackingLink(token="tok123", label="a link", case_id=case.id, user_id=user_id)
            session.add(link)
            session.flush()
            hit = TrackingHit(link_id=link.id, ip="1.2.3.4")
            session.add(hit)
            report = IntelligenceReport(title="a report", related_case_id=case.id)
            session.add(report)
            session.flush()
            ids = {
                "comment_id": comment.id, "note_id": note.id, "target_id": target.id,
                "link_id": link.id, "hit_id": hit.id, "report_id": report.id,
            }

        return case, inv.id, ids


def test_delete_case_removes_all_scoped_child_rows(app, user_a):
    from app.repositories.base import session_scope
    from app.models.investigation import Investigation
    from app.models.case_comment import CaseComment
    from app.models.case_note import CaseNote
    from app.models.watchlist import WatchlistTarget
    from app.models.tracking_link import TrackingLink
    from app.models.tracking_hit import TrackingHit
    from app.models.intelligence_report import IntelligenceReport

    case, inv_id, ids = _seed_full_case(app, user_a.id)

    with app.app_context():
        assert delete_case(case.id) is True
        assert get_case(case.id) is None

        with session_scope() as session:
            assert session.get(Investigation, inv_id) is None
            assert session.get(CaseComment, ids["comment_id"]) is None
            assert session.get(CaseNote, ids["note_id"]) is None
            assert session.get(WatchlistTarget, ids["target_id"]) is None
            assert session.get(TrackingLink, ids["link_id"]) is None
            assert session.get(TrackingHit, ids["hit_id"]) is None

            # Report itself survives — it's an export artifact, not
            # working case data — but its case reference is nulled out.
            report = session.get(IntelligenceReport, ids["report_id"])
            assert report is not None
            assert report.related_case_id is None


def test_delete_case_does_not_touch_another_case_data(app, user_a):
    """A second, untouched case's rows must survive deleting the first."""
    case_1, inv_1, _ = _seed_full_case(app, user_a.id)
    case_2, inv_2, _ = _seed_full_case(app, user_a.id)

    with app.app_context():
        from app.repositories.investigation_repository import get_investigation

        assert delete_case(case_1.id) is True
        assert get_case(case_2.id) is not None
        assert get_investigation(inv_2) is not None
        assert get_investigation(inv_1) is None


def test_delete_case_removed_data_no_longer_appears_on_map_or_graph(app, client, user_a):
    from tests.conftest import login

    case, _, _ = _seed_full_case(app, user_a.id)
    login(client, user_a.username)

    resp = client.get(f"/investigate/map/data?case_id={case.id}")
    assert resp.status_code == 200
    assert len(resp.get_json()["markers"]) == 1

    with app.app_context():
        delete_case(case.id)

    # The case is gone entirely now, so scoping to its (deleted) id is a
    # 404-ish "no access" rather than an empty result — access checks look
    # the case up first and find nothing.
    resp = client.get(f"/investigate/map/data?case_id={case.id}")
    assert resp.status_code == 403

    resp = client.get("/investigate/map/data")
    assert resp.status_code == 200
    assert resp.get_json()["markers"] == []


def test_delete_case_returns_false_for_nonexistent_case(app):
    with app.app_context():
        assert delete_case(999999) is False


# ── close_case() deletes the same scoped data, but keeps the Case row ────

def test_close_case_deletes_scoped_data_but_keeps_the_case(app, client, user_a):
    from tests.conftest import login
    from app.repositories.base import session_scope
    from app.models.investigation import Investigation
    from app.models.case_comment import CaseComment
    from app.models.case_note import CaseNote
    from app.models.watchlist import WatchlistTarget
    from app.models.tracking_link import TrackingLink
    from app.models.tracking_hit import TrackingHit
    from app.models.intelligence_report import IntelligenceReport

    case, inv_id, ids = _seed_full_case(app, user_a.id)
    login(client, user_a.username)

    resp = client.post(f"/cases/{case.id}/close")
    assert resp.status_code == 302

    with app.app_context():
        closed_case = get_case(case.id)
        assert closed_case is not None
        assert closed_case.status == "closed"

        with session_scope() as session:
            assert session.get(Investigation, inv_id) is None
            assert session.get(CaseComment, ids["comment_id"]) is None
            assert session.get(CaseNote, ids["note_id"]) is None
            assert session.get(WatchlistTarget, ids["target_id"]) is None
            assert session.get(TrackingLink, ids["link_id"]) is None
            assert session.get(TrackingHit, ids["hit_id"]) is None

            report = session.get(IntelligenceReport, ids["report_id"])
            assert report is not None
            assert report.related_case_id is None


def test_close_case_does_not_touch_another_case_data(app, client, user_a):
    from tests.conftest import login
    from app.repositories.investigation_repository import get_investigation

    case_1, inv_1, _ = _seed_full_case(app, user_a.id)
    case_2, inv_2, _ = _seed_full_case(app, user_a.id)
    login(client, user_a.username)

    resp = client.post(f"/cases/{case_1.id}/close")
    assert resp.status_code == 302

    with app.app_context():
        assert get_case(case_2.id) is not None
        assert get_investigation(inv_2) is not None
        assert get_investigation(inv_1) is None


# ── Editing a case's status to "closed" must clean up exactly like the
#    dedicated Close button — a second, easy-to-miss path into "closed"
#    that must not bypass the cleanup. ─────────────────────────────────────

def test_edit_case_status_to_closed_deletes_scoped_data(app, client, user_a):
    from tests.conftest import login
    from app.repositories.base import session_scope
    from app.models.investigation import Investigation
    from app.models.watchlist import WatchlistTarget

    case, inv_id, ids = _seed_full_case(app, user_a.id)
    login(client, user_a.username)

    resp = client.post(f"/cases/{case.id}/edit", data={
        "title": case.title, "description": case.description,
        "priority": case.priority, "status": "closed",
    })
    assert resp.status_code == 302

    with app.app_context():
        closed_case = get_case(case.id)
        assert closed_case is not None
        assert closed_case.status == "closed"

        with session_scope() as session:
            assert session.get(Investigation, inv_id) is None
            assert session.get(WatchlistTarget, ids["target_id"]) is None


def test_edit_case_without_status_change_does_not_delete_data(app, client, user_a):
    from tests.conftest import login
    from app.repositories.investigation_repository import get_investigation

    case, inv_id, _ = _seed_full_case(app, user_a.id)
    login(client, user_a.username)

    resp = client.post(f"/cases/{case.id}/edit", data={
        "title": "Renamed", "description": case.description,
        "priority": case.priority, "status": "open",
    })
    assert resp.status_code == 302

    with app.app_context():
        assert get_case(case.id).title == "Renamed"
        assert get_investigation(inv_id) is not None


def test_edit_case_already_closed_does_not_redelete_or_error(app, client, user_a):
    """Editing an already-closed case (e.g. just changing its title) must
    not attempt cleanup again — was_closed guards against a redundant
    second delete pass."""
    from tests.conftest import login

    case, _, _ = _seed_full_case(app, user_a.id)
    login(client, user_a.username)

    resp = client.post(f"/cases/{case.id}/close")
    assert resp.status_code == 302

    resp = client.post(f"/cases/{case.id}/edit", data={
        "title": "Still Closed", "description": case.description,
        "priority": case.priority, "status": "closed",
    })
    assert resp.status_code == 302

    with app.app_context():
        edited = get_case(case.id)
        assert edited.status == "closed"
        assert edited.title == "Still Closed"
