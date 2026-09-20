"""app.services.case_backup + the /cases/<id>/backup and /cases/<id>/restore
routes — encrypted per-case backup and restore.

Closing or deleting a case cascades to permanently wipe its data (see
tests/test_case_delete_cascade.py); this gives a way to keep it first: an
AES-256-encrypted zip (password chosen at download time, never stored)
that a restore can later re-create into a case with original timestamps
preserved, "as if closing never deleted it."
"""
import io
import json

from tests.conftest import login
from app.services import case_backup


def _seed_full_case(app, user, case):
    from app.repositories.investigation_repository import create_investigation
    from app.repositories.case_comment_repository import add_comment
    from app.repositories.case_note_repository import add_note
    from app.repositories.watchlist_repository import add_target
    from app.repositories.tracking_repository import create_link, record_hit

    with app.app_context():
        create_investigation(kind="domain", query="example.com",
            result_json=json.dumps({"domain": "example.com"}),
            user_id=user.id, case_id=case.id, confidence="CONFIRMED")
        add_comment(case.id, user.id, user.username, "A team note.")
        add_note(case.id, user.id, user.username, "lead", "A journal entry.")
        add_target("target.com", "domain", user.id, case_id=case.id, notes="watch this")
        link = create_link("My Link", user.id, case_id=case.id,
                            decoy_mode="redirect", redirect_url="https://example.com")
        record_hit(link.id, ip="1.2.3.4", country="US", city="NYC")


def _wipe_case_data(app, case_id):
    from app.repositories.base import session_scope
    from app.models.investigation import Investigation
    from app.models.case_comment import CaseComment
    from app.models.case_note import CaseNote
    from app.models.watchlist import WatchlistTarget
    from app.models.tracking_link import TrackingLink
    from app.models.tracking_hit import TrackingHit
    from sqlmodel import select

    with app.app_context(), session_scope() as session:
        for model in (Investigation, CaseComment, CaseNote, WatchlistTarget):
            for row in session.exec(select(model).where(model.case_id == case_id)).all():
                session.delete(row)
        for link in session.exec(select(TrackingLink).where(TrackingLink.case_id == case_id)).all():
            for hit in session.exec(select(TrackingHit).where(TrackingHit.link_id == link.id)).all():
                session.delete(hit)
            session.delete(link)


# ── app.services.case_backup ─────────────────────────────────────────────────

def test_build_and_restore_round_trip_preserves_original_timestamps(app, user_a, case_of_a):
    _seed_full_case(app, user_a, case_of_a)
    with app.app_context():
        from app.repositories.investigation_repository import list_by_case
        original_created_at = list_by_case(case_of_a.id)[0].created_at
        zip_bytes = case_backup.build_backup_zip(case_of_a, "hunter22")

    _wipe_case_data(app, case_of_a.id)
    with app.app_context():
        from app.repositories.investigation_repository import list_by_case
        assert list_by_case(case_of_a.id) == []

        counts = case_backup.restore_backup_zip(case_of_a.id, zip_bytes, "hunter22")
        assert counts == {
            "investigations": 1, "comments": 1, "notes": 1,
            "watchlist": 1, "tracking_links": 1, "tracking_hits": 1,
        }

        restored = list_by_case(case_of_a.id)
        assert len(restored) == 1
        assert restored[0].query == "example.com"
        assert restored[0].created_at == original_created_at


def test_restore_generates_a_fresh_tracking_link_token(app, user_a, case_of_a):
    from app.repositories.tracking_repository import create_link, list_links_by_case
    with app.app_context():
        original = create_link("A Link", user_a.id, case_id=case_of_a.id)
        original_token = original.token
        zip_bytes = case_backup.build_backup_zip(case_of_a, "hunter22")

    _wipe_case_data(app, case_of_a.id)
    with app.app_context():
        case_backup.restore_backup_zip(case_of_a.id, zip_bytes, "hunter22")
        restored_links = list_links_by_case(case_of_a.id)
        assert len(restored_links) == 1
        assert restored_links[0].token != original_token


def test_wrong_password_raises_and_writes_nothing(app, user_a, case_of_a):
    _seed_full_case(app, user_a, case_of_a)
    with app.app_context():
        zip_bytes = case_backup.build_backup_zip(case_of_a, "hunter22")

    _wipe_case_data(app, case_of_a.id)
    with app.app_context():
        try:
            case_backup.restore_backup_zip(case_of_a.id, zip_bytes, "wrong-password")
            assert False, "expected WrongPasswordError"
        except case_backup.WrongPasswordError:
            pass

        from app.repositories.investigation_repository import list_by_case
        assert list_by_case(case_of_a.id) == []


def test_garbage_bytes_raise_invalid_backup_error(app):
    with app.app_context():
        try:
            case_backup.restore_backup_zip(1, b"not a zip file at all", "anypass")
            assert False, "expected InvalidBackupError"
        except case_backup.InvalidBackupError:
            pass


def test_empty_case_backup_restores_zero_of_everything(app, user_a, case_of_a):
    with app.app_context():
        zip_bytes = case_backup.build_backup_zip(case_of_a, "hunter22")
        counts = case_backup.restore_backup_zip(case_of_a.id, zip_bytes, "hunter22")
    assert counts == {
        "investigations": 0, "comments": 0, "notes": 0,
        "watchlist": 0, "tracking_links": 0, "tracking_hits": 0,
    }


# ── Routes ────────────────────────────────────────────────────────────────

def test_backup_route_requires_matching_passwords(app, client, user_a, case_of_a):
    login(client, user_a.username)
    resp = client.post(f"/cases/{case_of_a.id}/backup",
                       data={"password": "hunter22", "password_confirm": "different"},
                       follow_redirects=True)
    assert b"do not match" in resp.data


def test_backup_route_requires_minimum_password_length(app, client, user_a, case_of_a):
    login(client, user_a.username)
    resp = client.post(f"/cases/{case_of_a.id}/backup",
                       data={"password": "short", "password_confirm": "short"},
                       follow_redirects=True)
    assert b"at least 8 characters" in resp.data


def test_backup_route_downloads_a_zip(app, client, user_a, case_of_a):
    _seed_full_case(app, user_a, case_of_a)
    login(client, user_a.username)
    resp = client.post(f"/cases/{case_of_a.id}/backup",
                       data={"password": "hunter22", "password_confirm": "hunter22"})
    assert resp.status_code == 200
    assert resp.headers["Content-Type"] == "application/zip"
    assert len(resp.data) > 0


def test_restore_route_round_trips_through_the_full_stack(app, client, user_a, case_of_a):
    _seed_full_case(app, user_a, case_of_a)
    login(client, user_a.username)
    backup_resp = client.post(f"/cases/{case_of_a.id}/backup",
                              data={"password": "hunter22", "password_confirm": "hunter22"})
    zip_bytes = backup_resp.data

    _wipe_case_data(app, case_of_a.id)

    restore_resp = client.post(
        f"/cases/{case_of_a.id}/restore",
        data={"backup_file": (io.BytesIO(zip_bytes), "backup.zip"), "password": "hunter22"},
        content_type="multipart/form-data", follow_redirects=True,
    )
    assert restore_resp.status_code == 200
    assert b"Restored 1 investigation" in restore_resp.data

    with app.app_context():
        from app.repositories.investigation_repository import list_by_case
        assert len(list_by_case(case_of_a.id)) == 1


def test_restore_route_rejects_wrong_password(app, client, user_a, case_of_a):
    _seed_full_case(app, user_a, case_of_a)
    login(client, user_a.username)
    backup_resp = client.post(f"/cases/{case_of_a.id}/backup",
                              data={"password": "hunter22", "password_confirm": "hunter22"})
    resp = client.post(
        f"/cases/{case_of_a.id}/restore",
        data={"backup_file": (io.BytesIO(backup_resp.data), "backup.zip"), "password": "nope"},
        content_type="multipart/form-data", follow_redirects=True,
    )
    assert b"Incorrect password" in resp.data


def test_backup_route_rejects_user_without_access(app, client, user_b, case_of_a):
    login(client, user_b.username)
    resp = client.get(f"/cases/{case_of_a.id}/backup")
    assert resp.status_code == 403


def test_restore_route_rejects_user_without_edit_access(app, client, user_b, case_of_a):
    login(client, user_b.username)
    resp = client.get(f"/cases/{case_of_a.id}/restore")
    assert resp.status_code == 403
