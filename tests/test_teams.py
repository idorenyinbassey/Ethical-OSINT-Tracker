"""Team management: CRUD via the /teams routes, plus the repository-level
detach fix (create_team/add_team_member used to raise DetachedInstanceError
outside their session — a pre-existing bug this feature surfaced)."""
from tests.conftest import login
from app.repositories.team_repository import (
    get_membership, list_team_members, count_owners,
)


def test_create_team_and_add_member_does_not_raise_detached_instance_error(app, client, user_a, user_b):
    """Regression test for the DetachedInstanceError bug: create_team()
    and add_team_member() used to return session-bound objects whose
    attributes couldn't be accessed after the session closed."""
    import os
    team_name = f"Red Team {os.urandom(4).hex()}"  # unique — the test DB is shared across the whole suite
    login(client, user_a.username)
    resp = client.post("/teams/create", data={"name": team_name, "description": "x"},
                        follow_redirects=True)
    assert resp.status_code == 200
    assert team_name.encode() in resp.data

    with app.app_context():
        from app.repositories.team_repository import list_teams_for_user
        team = next(t for t in list_teams_for_user(user_a.id) if t.name == team_name)
        # user_a is auto-added as owner on team creation
        assert get_membership(team.id, user_a.id).role == "owner"

    teams_page = client.get(f"/teams/{team.id}")
    assert teams_page.status_code == 200

    resp = client.post(f"/teams/{team.id}/members/add", data={"username": user_b.username, "role": "analyst"},
                        follow_redirects=True)
    assert resp.status_code == 200
    with app.app_context():
        assert get_membership(team.id, user_b.id).role == "analyst"


def test_non_member_cannot_view_team(app, client, user_a, user_b, team_a):
    login(client, user_b.username)
    resp = client.get(f"/teams/{team_a.id}")
    assert resp.status_code == 403


def test_member_can_view_but_not_manage(app, client, user_a, user_b, team_a):
    with app.app_context():
        from app.repositories.team_repository import add_team_member
        add_team_member(team_a.id, user_b.id, role="member")

    login(client, user_b.username)
    resp = client.get(f"/teams/{team_a.id}")
    assert resp.status_code == 200

    # A plain member cannot add other members or delete the team.
    resp = client.post(f"/teams/{team_a.id}/members/add",
                        data={"username": user_a.username, "role": "member"})
    assert resp.status_code == 403
    resp = client.post(f"/teams/{team_a.id}/delete")
    assert resp.status_code == 403


def test_invalid_role_rejected(app, client, user_a, team_a):
    login(client, user_a.username)
    resp = client.post(f"/teams/{team_a.id}/members/add",
                        data={"username": user_a.username, "role": "supreme_leader"},
                        follow_redirects=True)
    assert resp.status_code == 200
    assert b"invalid role" in resp.data.lower()


def test_cannot_add_duplicate_member(app, client, user_a, user_b, team_a):
    login(client, user_a.username)
    client.post(f"/teams/{team_a.id}/members/add", data={"username": user_b.username, "role": "member"})
    resp = client.post(f"/teams/{team_a.id}/members/add",
                        data={"username": user_b.username, "role": "analyst"},
                        follow_redirects=True)
    assert resp.status_code == 200
    assert b"already a member" in resp.data.lower()


def test_cannot_remove_last_owner(app, client, user_a, team_a):
    login(client, user_a.username)
    assert count_owners(team_a.id) == 1
    resp = client.post(f"/teams/{team_a.id}/members/{user_a.id}/remove", follow_redirects=True)
    assert resp.status_code == 200
    assert b"cannot remove the last owner" in resp.data.lower()
    with app.app_context():
        assert get_membership(team_a.id, user_a.id) is not None


def test_cannot_demote_last_owner(app, client, user_a, team_a):
    login(client, user_a.username)
    resp = client.post(f"/teams/{team_a.id}/members/{user_a.id}/role",
                        data={"role": "member"}, follow_redirects=True)
    assert resp.status_code == 200
    assert b"cannot demote the last owner" in resp.data.lower()
    with app.app_context():
        assert get_membership(team_a.id, user_a.id).role == "owner"


def test_second_owner_allows_demotion(app, client, user_a, user_b, team_a):
    with app.app_context():
        from app.repositories.team_repository import add_team_member
        add_team_member(team_a.id, user_b.id, role="owner")

    login(client, user_a.username)
    resp = client.post(f"/teams/{team_a.id}/members/{user_a.id}/role",
                        data={"role": "member"}, follow_redirects=True)
    assert resp.status_code == 200
    with app.app_context():
        assert get_membership(team_a.id, user_a.id).role == "member"


def test_delete_team_requires_owner_role(app, client, user_a, user_b, team_a):
    with app.app_context():
        from app.repositories.team_repository import add_team_member
        add_team_member(team_a.id, user_b.id, role="admin")

    login(client, user_b.username)
    resp = client.post(f"/teams/{team_a.id}/delete")
    assert resp.status_code == 403
    client.get("/logout")

    login(client, user_a.username)
    resp = client.post(f"/teams/{team_a.id}/delete", follow_redirects=True)
    assert resp.status_code == 200
    with app.app_context():
        assert list_team_members(team_a.id) == []
