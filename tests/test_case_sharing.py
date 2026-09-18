"""Case sharing via teams: the permission matrix in app/utils/authz.py,
list_cases_for_user, and the /cases/<id>/share route."""
from tests.conftest import login
from app.repositories.team_repository import add_team_member
from app.repositories.case_repository import list_cases_for_user, get_case
from app.utils.authz import can_access_case


def _share(app, case, team):
    with app.app_context():
        from app.repositories.case_repository import update_case
        update_case(case.id, team_id=team.id)
        return get_case(case.id)


def test_unshared_case_is_owner_only(app, client, user_a, user_b, case_of_a):
    login(client, user_b.username)
    resp = client.get(f"/cases/{case_of_a.id}")
    assert resp.status_code == 403


def test_share_requires_edit_access(app, client, user_a, user_b, case_of_a, team_a):
    login(client, user_b.username)
    resp = client.post(f"/cases/{case_of_a.id}/share", data={"team_id": str(team_a.id)})
    assert resp.status_code == 403


def test_owner_can_share_only_with_own_team(app, client, user_a, case_of_a):
    """Sharing with a team the user doesn't belong to must be rejected —
    otherwise anyone could leak a case into an arbitrary team_id."""
    login(client, user_a.username)
    resp = client.post(f"/cases/{case_of_a.id}/share", data={"team_id": "99999"},
                        follow_redirects=True)
    assert resp.status_code == 200
    assert b"you can only share" in resp.data.lower()
    with app.app_context():
        assert get_case(case_of_a.id).team_id is None


def test_owner_shares_case_with_team(app, client, user_a, case_of_a, team_a):
    login(client, user_a.username)
    resp = client.post(f"/cases/{case_of_a.id}/share", data={"team_id": str(team_a.id)},
                        follow_redirects=True)
    assert resp.status_code == 200
    with app.app_context():
        assert get_case(case_of_a.id).team_id == team_a.id


def test_member_role_can_read_and_comment_not_edit_or_delete(app, user_a, user_b, case_of_a, team_a, client):
    with app.app_context():
        add_team_member(team_a.id, user_b.id, role="member")
    shared = _share(app, case_of_a, team_a)

    with app.app_context():
        assert can_access_case(shared, user_b, action="read") is True
        assert can_access_case(shared, user_b, action="comment") is True
        assert can_access_case(shared, user_b, action="export") is False
        assert can_access_case(shared, user_b, action="edit") is False
        assert can_access_case(shared, user_b, action="delete") is False

    login(client, user_b.username)
    assert client.get(f"/cases/{case_of_a.id}").status_code == 200
    assert client.get(f"/cases/{case_of_a.id}/edit").status_code == 403
    assert client.post(f"/cases/{case_of_a.id}/delete").status_code == 403
    # 'member' role lacks "export" — _get_case_with_access aborts 403.
    assert client.get(f"/cases/{case_of_a.id}/export/pdf").status_code == 403


def test_analyst_role_can_export(app, user_a, user_b, case_of_a, team_a):
    with app.app_context():
        add_team_member(team_a.id, user_b.id, role="analyst")
    shared = _share(app, case_of_a, team_a)
    with app.app_context():
        assert can_access_case(shared, user_b, action="export") is True
        assert can_access_case(shared, user_b, action="edit") is False


def test_admin_role_can_edit_not_delete(app, user_a, user_b, case_of_a, team_a):
    with app.app_context():
        add_team_member(team_a.id, user_b.id, role="admin")
    shared = _share(app, case_of_a, team_a)
    with app.app_context():
        assert can_access_case(shared, user_b, action="edit") is True
        assert can_access_case(shared, user_b, action="delete") is False


def test_team_owner_role_has_full_access(app, user_a, user_b, case_of_a, team_a):
    with app.app_context():
        add_team_member(team_a.id, user_b.id, role="owner")
    shared = _share(app, case_of_a, team_a)
    with app.app_context():
        assert can_access_case(shared, user_b, action="delete") is True


def test_outsider_denied_even_with_shared_case(app, user_a, user_b, case_of_a, team_a):
    """user_b is NOT a member of team_a — sharing to team_a must not grant them access."""
    shared = _share(app, case_of_a, team_a)
    with app.app_context():
        assert can_access_case(shared, user_b, action="read") is False


def test_case_owner_always_has_full_access_regardless_of_team_role(app, user_a, case_of_a, team_a):
    """Even if the case is shared and the owner's own team role is 'member'
    (lowest), the case owner_user_id always wins."""
    with app.app_context():
        add_team_member(team_a.id, user_a.id, role="member")  # already owner from fixture; role irrelevant
    shared = _share(app, case_of_a, team_a)
    with app.app_context():
        assert can_access_case(shared, user_a, action="delete") is True


def test_list_cases_for_user_includes_shared_cases(app, user_a, user_b, case_of_a, team_a):
    with app.app_context():
        add_team_member(team_a.id, user_b.id, role="member")
    _share(app, case_of_a, team_a)
    with app.app_context():
        ids = {c.id for c in list_cases_for_user(user_b.id)}
        assert case_of_a.id in ids


def test_list_cases_for_user_excludes_unshared_cases_of_others(app, user_a, user_b, case_of_a):
    with app.app_context():
        ids = {c.id for c in list_cases_for_user(user_b.id)}
        assert case_of_a.id not in ids


def test_unshare_case(app, client, user_a, case_of_a, team_a):
    _share(app, case_of_a, team_a)
    login(client, user_a.username)
    resp = client.post(f"/cases/{case_of_a.id}/share", data={"team_id": ""}, follow_redirects=True)
    assert resp.status_code == 200
    with app.app_context():
        assert get_case(case_of_a.id).team_id is None
