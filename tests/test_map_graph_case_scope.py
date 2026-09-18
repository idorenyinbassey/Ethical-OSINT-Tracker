"""app.routes.investigation — /investigate/map/data and /investigate/graph/data
now accept ?case_id=<id> to scope to a single case's investigations (any
team member's, per can_access_case), for the report-snapshot renderer and
an optional case-scoped view in the UI. Without the param, both routes
keep their pre-existing account-wide behavior."""
import json
from tests.conftest import login


def _seed_ip_investigation(app, user, case):
    from app.repositories.investigation_repository import create_investigation
    with app.app_context():
        create_investigation(
            kind="ip", query="8.8.8.8",
            result_json=json.dumps({"ip": "8.8.8.8", "geo": {"lat": 37.4, "lon": -122.08}}),
            user_id=user.id, case_id=case.id, confidence="CONFIRMED",
        )


def test_map_data_without_case_id_is_account_wide(app, client, user_a, case_of_a):
    login(client, user_a.username)
    _seed_ip_investigation(app, user_a, case_of_a)

    resp = client.get("/investigate/map/data")
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data["markers"]) == 1


def test_map_data_with_case_id_scopes_to_that_case(app, client, user_a, case_of_a):
    from app.repositories.case_repository import create_case
    from app.repositories.investigation_repository import create_investigation

    login(client, user_a.username)
    _seed_ip_investigation(app, user_a, case_of_a)

    with app.app_context():
        other_case = create_case("Other Case", "", owner_user_id=user_a.id)
        create_investigation(
            kind="ip", query="1.1.1.1",
            result_json=json.dumps({"ip": "1.1.1.1", "geo": {"lat": 10.0, "lon": 20.0}}),
            user_id=user_a.id, case_id=other_case.id, confidence="CONFIRMED",
        )

    resp = client.get(f"/investigate/map/data?case_id={case_of_a.id}")
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data["markers"]) == 1
    assert data["markers"][0]["label"] == "8.8.8.8"


def test_map_data_denies_case_id_the_user_cannot_access(app, client, user_a, user_b, case_of_a):
    login(client, user_b.username)
    resp = client.get(f"/investigate/map/data?case_id={case_of_a.id}")
    assert resp.status_code == 403


def test_map_data_case_id_shows_other_team_members_investigations(app, client, user_a, user_b):
    """A case-scoped map must show investigations logged by ANY team
    member with access, not just the requester's own — unlike the
    account-wide default view, which is intentionally per-user."""
    from app.repositories.case_repository import create_case, update_case
    from app.repositories.team_repository import create_team, add_team_member
    from app.repositories.investigation_repository import create_investigation

    with app.app_context():
        team = create_team("Shared Team", "", owner_user_id=user_a.id)
        add_team_member(team.id, user_a.id, role="owner")
        add_team_member(team.id, user_b.id, role="analyst")
        shared_case = create_case("Shared Case", "", owner_user_id=user_a.id)
        update_case(shared_case.id, team_id=team.id)
        create_investigation(
            kind="ip", query="9.9.9.9",
            result_json=json.dumps({"ip": "9.9.9.9", "geo": {"lat": 1.0, "lon": 2.0}}),
            user_id=user_a.id, case_id=shared_case.id, confidence="CONFIRMED",
        )

    login(client, user_b.username)
    resp = client.get(f"/investigate/map/data?case_id={shared_case.id}")
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data["markers"]) == 1
    assert data["markers"][0]["label"] == "9.9.9.9"


def test_graph_data_without_case_id_is_account_wide(app, client, user_a, case_of_a):
    login(client, user_a.username)
    resp = client.get("/investigate/graph/data")
    assert resp.status_code == 200
    data = resp.get_json()
    case_nodes = [n for n in data["nodes"] if n["group"] == "case"]
    assert any(n["id"] == f"case-{case_of_a.id}" for n in case_nodes)


def test_graph_data_with_case_id_scopes_to_one_case(app, client, user_a, case_of_a):
    from app.repositories.case_repository import create_case

    login(client, user_a.username)
    with app.app_context():
        other_case = create_case("Other Case 2", "", owner_user_id=user_a.id)

    resp = client.get(f"/investigate/graph/data?case_id={case_of_a.id}")
    assert resp.status_code == 200
    data = resp.get_json()
    case_nodes = [n for n in data["nodes"] if n["group"] == "case"]
    assert len(case_nodes) == 1
    assert case_nodes[0]["id"] == f"case-{case_of_a.id}"


def test_graph_data_denies_case_id_the_user_cannot_access(app, client, user_a, user_b, case_of_a):
    login(client, user_b.username)
    resp = client.get(f"/investigate/graph/data?case_id={case_of_a.id}")
    assert resp.status_code == 403


def test_map_page_forwards_case_id_query_param(app, client, user_a, case_of_a):
    """The /investigate/map page itself must render (case_id forwarding
    to the data fetch happens client-side in JS, so this just checks the
    page loads with the param present)."""
    login(client, user_a.username)
    resp = client.get(f"/investigate/map?case_id={case_of_a.id}")
    assert resp.status_code == 200


# ── Explicit multi-case comparison (repeated ?case_id=) ───────────────────
#
# Cases are isolated by default (single case_id, or no case_id at all).
# Passing MULTIPLE case_id params is how an investigator explicitly opts
# into comparing cases side by side — it must return the union of exactly
# those cases' data, not silently expand to every case the user owns.

def test_map_data_multi_case_id_returns_union_of_both_cases(app, client, user_a, case_of_a):
    from app.repositories.case_repository import create_case
    from app.repositories.investigation_repository import create_investigation

    login(client, user_a.username)
    _seed_ip_investigation(app, user_a, case_of_a)

    with app.app_context():
        other_case = create_case("Other Case", "", owner_user_id=user_a.id)
        create_investigation(
            kind="ip", query="1.1.1.1",
            result_json=json.dumps({"ip": "1.1.1.1", "geo": {"lat": 10.0, "lon": 20.0}}),
            user_id=user_a.id, case_id=other_case.id, confidence="CONFIRMED",
        )
        third_case = create_case("Third Case (not selected)", "", owner_user_id=user_a.id)
        create_investigation(
            kind="ip", query="2.2.2.2",
            result_json=json.dumps({"ip": "2.2.2.2", "geo": {"lat": 5.0, "lon": 6.0}}),
            user_id=user_a.id, case_id=third_case.id, confidence="CONFIRMED",
        )

    resp = client.get(f"/investigate/map/data?case_id={case_of_a.id}&case_id={other_case.id}")
    assert resp.status_code == 200
    data = resp.get_json()
    labels = {m["label"] for m in data["markers"]}
    assert labels == {"8.8.8.8", "1.1.1.1"}


def test_map_data_multi_case_id_denies_a_case_the_user_cannot_access(app, client, user_a, user_b, case_of_a):
    with app.app_context():
        from app.repositories.case_repository import create_case
        own_case = create_case("User B's own case", "", owner_user_id=user_b.id)

    login(client, user_b.username)
    resp = client.get(f"/investigate/map/data?case_id={own_case.id}&case_id={case_of_a.id}")
    assert resp.status_code == 403


def test_graph_data_multi_case_id_returns_both_case_bubbles(app, client, user_a, case_of_a):
    from app.repositories.case_repository import create_case

    login(client, user_a.username)
    with app.app_context():
        other_case = create_case("Other Case 2", "", owner_user_id=user_a.id)
        third_case = create_case("Third Case (not selected)", "", owner_user_id=user_a.id)

    resp = client.get(f"/investigate/graph/data?case_id={case_of_a.id}&case_id={other_case.id}")
    assert resp.status_code == 200
    data = resp.get_json()
    case_node_ids = {n["id"] for n in data["nodes"] if n["group"] == "case"}
    assert case_node_ids == {f"case-{case_of_a.id}", f"case-{other_case.id}"}
    assert f"case-{third_case.id}" not in case_node_ids


def test_graph_data_multi_case_tooltip_shows_case_title(app, client, user_a, case_of_a):
    """When comparing 2+ cases, each investigation node's tooltip should
    say which case it belongs to, so results stay visually distinguishable
    rather than blending together."""
    from app.repositories.case_repository import create_case

    login(client, user_a.username)
    _seed_ip_investigation(app, user_a, case_of_a)
    with app.app_context():
        other_case = create_case("Other Case 3", "", owner_user_id=user_a.id)

    resp = client.get(f"/investigate/graph/data?case_id={case_of_a.id}&case_id={other_case.id}")
    assert resp.status_code == 200
    data = resp.get_json()
    inv_nodes = [n for n in data["nodes"] if n["group"] == "ip"]
    assert len(inv_nodes) == 1
    assert f"Case: {case_of_a.title}" in inv_nodes[0]["title"]


def test_graph_data_single_case_tooltip_omits_case_title(app, client, user_a, case_of_a):
    """The single-case (default, isolated) view doesn't need a case label
    on every node — it's already implied by being on that case's own
    graph, so the tooltip stays uncluttered."""
    login(client, user_a.username)
    _seed_ip_investigation(app, user_a, case_of_a)

    resp = client.get(f"/investigate/graph/data?case_id={case_of_a.id}")
    assert resp.status_code == 200
    data = resp.get_json()
    inv_nodes = [n for n in data["nodes"] if n["group"] == "ip"]
    assert len(inv_nodes) == 1
    assert "Case:" not in inv_nodes[0]["title"]
