"""Case delete/close is gated to site-wide admins only, with the admin's
own password re-entered before the action fires — a case's owner (or a
team "owner" role) no longer gets self-service delete/close, and an
ownerless case is only reachable by an admin. See app/utils/authz.py's
module docstring and app/routes/cases.py's delete()/close_case()/edit()
for the implementation this exercises.
"""
from tests.conftest import login, PASSWORD


def test_owner_cannot_delete_own_case_without_being_admin(client, user_a, case_of_a):
    login(client, user_a.username)
    resp = client.post(f"/cases/{case_of_a.id}/delete", data={"password": PASSWORD})
    assert resp.status_code == 403


def test_owner_cannot_close_own_case_without_being_admin(client, user_a, case_of_a):
    login(client, user_a.username)
    resp = client.post(f"/cases/{case_of_a.id}/close", data={"password": PASSWORD})
    assert resp.status_code == 403


def test_owner_cannot_close_via_edit_form_without_being_admin(app, client, user_a, case_of_a):
    from app.repositories.case_repository import get_case

    login(client, user_a.username)
    resp = client.post(f"/cases/{case_of_a.id}/edit", data={
        "title": case_of_a.title, "description": case_of_a.description,
        "priority": case_of_a.priority, "status": "closed", "password": PASSWORD,
    })
    assert resp.status_code == 200
    with app.app_context():
        assert get_case(case_of_a.id).status != "closed"


def test_admin_delete_with_wrong_password_leaves_case_untouched(app, client, admin_user, case_of_a):
    from app.repositories.case_repository import get_case

    login(client, admin_user.username)
    resp = client.post(f"/cases/{case_of_a.id}/delete", data={"password": "definitely-wrong"})
    assert resp.status_code == 302
    with app.app_context():
        assert get_case(case_of_a.id) is not None


def test_admin_close_with_wrong_password_leaves_case_open(app, client, admin_user, case_of_a):
    from app.repositories.case_repository import get_case

    login(client, admin_user.username)
    resp = client.post(f"/cases/{case_of_a.id}/close", data={"password": "definitely-wrong"})
    assert resp.status_code == 302
    with app.app_context():
        assert get_case(case_of_a.id).status != "closed"


def test_admin_delete_with_correct_password_succeeds(app, client, admin_user, case_of_a):
    from app.repositories.case_repository import get_case

    login(client, admin_user.username)
    resp = client.post(f"/cases/{case_of_a.id}/delete", data={"password": PASSWORD})
    assert resp.status_code == 302
    with app.app_context():
        assert get_case(case_of_a.id) is None


def test_admin_delete_missing_password_field_is_rejected(app, client, admin_user, case_of_a):
    """No password field submitted at all (e.g. a crafted request bypassing
    the form) must be treated the same as a wrong one, not skip the check."""
    from app.repositories.case_repository import get_case

    login(client, admin_user.username)
    resp = client.post(f"/cases/{case_of_a.id}/delete")
    assert resp.status_code == 302
    with app.app_context():
        assert get_case(case_of_a.id) is not None


def test_non_admin_cannot_delete_an_ownerless_case(app, client, user_a):
    from app.repositories.case_repository import create_case

    with app.app_context():
        case = create_case("Orphan Case", "no owner", owner_user_id=None)
    login(client, user_a.username)

    resp = client.get(f"/cases/{case.id}")
    assert resp.status_code == 403

    resp = client.post(f"/cases/{case.id}/delete", data={"password": PASSWORD})
    assert resp.status_code == 403


def test_admin_can_read_and_delete_an_ownerless_case(app, client, admin_user):
    from app.repositories.case_repository import create_case, get_case

    with app.app_context():
        case = create_case("Orphan Case", "no owner", owner_user_id=None)
    login(client, admin_user.username)

    resp = client.get(f"/cases/{case.id}")
    assert resp.status_code == 200

    resp = client.post(f"/cases/{case.id}/delete", data={"password": PASSWORD})
    assert resp.status_code == 302
    with app.app_context():
        assert get_case(case.id) is None


def test_admin_can_read_and_edit_a_case_they_do_not_own(app, client, admin_user, user_a, case_of_a):
    """A global admin needs at least read/edit reach into a case they
    don't own — otherwise they could never discover it in order to
    exercise the admin-only delete/close in the first place."""
    from app.repositories.case_repository import get_case

    login(client, admin_user.username)
    resp = client.get(f"/cases/{case_of_a.id}")
    assert resp.status_code == 200

    resp = client.post(f"/cases/{case_of_a.id}/edit", data={
        "title": "Renamed by admin", "description": case_of_a.description,
        "priority": case_of_a.priority, "status": case_of_a.status,
    })
    assert resp.status_code == 302
    with app.app_context():
        assert get_case(case_of_a.id).title == "Renamed by admin"
