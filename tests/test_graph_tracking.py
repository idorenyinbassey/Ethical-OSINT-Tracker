"""app.routes.investigation graph_data() now folds in Link Tracker hits
(app/models/tracking_link.py / tracking_hit.py — a data model separate
from Investigation) as graph nodes, and registers each hit's IP into the
same entity-hub map used for Investigation-sourced entities, so a tracked
visitor's IP can link up with an unrelated IP Lookup investigation on that
same address. Mirrors tests/test_map_graph_case_scope.py's case-scoping
pattern, since tracking data needs the identical read-access checks."""
import json
from tests.conftest import login


def _seed_link_and_hit(app, user, case=None, ip="203.0.113.5"):
    from app.repositories.tracking_repository import create_link, record_hit
    with app.app_context():
        link = create_link("Test Link", user_id=user.id, case_id=case.id if case else None)
        record_hit(link.id, hit_type="link", ip=ip)
        return link


def test_graph_data_includes_own_tracking_hit_by_default(app, client, user_a):
    login(client, user_a.username)
    _seed_link_and_hit(app, user_a)

    resp = client.get("/investigate/graph/data")
    assert resp.status_code == 200
    data = resp.get_json()

    link_nodes = [n for n in data["nodes"] if n["group"] == "tracking_link"]
    hit_nodes = [n for n in data["nodes"] if n["group"] == "tracking_hit"]
    assert len(link_nodes) == 1
    assert len(hit_nodes) == 1
    assert hit_nodes[0]["label"] == "203.0.113.5"

    hit_edges = [e for e in data["edges"] if e["edge_type"] == "tracking_hit"]
    assert len(hit_edges) == 1
    assert hit_edges[0]["from"] == link_nodes[0]["id"]
    assert hit_edges[0]["to"] == hit_nodes[0]["id"]


def test_graph_data_does_not_leak_other_users_tracking_hits(app, client, user_a, user_b):
    login(client, user_a.username)
    _seed_link_and_hit(app, user_b)  # belongs to user_b, not the logged-in user

    resp = client.get("/investigate/graph/data")
    assert resp.status_code == 200
    data = resp.get_json()

    assert [n for n in data["nodes"] if n["group"] == "tracking_link"] == []
    assert [n for n in data["nodes"] if n["group"] == "tracking_hit"] == []


def test_graph_data_case_scoped_shows_other_team_members_tracking_links(app, client, user_a, user_b):
    """Mirrors test_map_graph_case_scope.py's
    test_map_data_case_id_shows_other_team_members_investigations — a
    case-scoped graph must show tracking links logged by ANY team member
    with read access, not just the requester's own."""
    from app.repositories.case_repository import create_case, update_case
    from app.repositories.team_repository import create_team, add_team_member
    from app.repositories.tracking_repository import create_link, record_hit

    with app.app_context():
        team = create_team("Shared Team", "", owner_user_id=user_a.id)
        add_team_member(team.id, user_a.id, role="owner")
        add_team_member(team.id, user_b.id, role="analyst")
        shared_case = create_case("Shared Case", "", owner_user_id=user_a.id)
        update_case(shared_case.id, team_id=team.id)
        link = create_link("Shared Link", user_id=user_a.id, case_id=shared_case.id)
        record_hit(link.id, hit_type="link", ip="198.51.100.9")

    login(client, user_b.username)
    resp = client.get(f"/investigate/graph/data?case_id={shared_case.id}")
    assert resp.status_code == 200
    data = resp.get_json()

    assert len([n for n in data["nodes"] if n["group"] == "tracking_link"]) == 1
    hit_nodes = [n for n in data["nodes"] if n["group"] == "tracking_hit"]
    assert len(hit_nodes) == 1
    assert hit_nodes[0]["label"] == "198.51.100.9"


def test_graph_data_denies_case_id_the_user_cannot_access_even_with_tracking_data(app, client, user_a, user_b, case_of_a):
    from app.repositories.tracking_repository import create_link, record_hit
    with app.app_context():
        link = create_link("Private Link", user_id=user_a.id, case_id=case_of_a.id)
        record_hit(link.id, hit_type="link", ip="203.0.113.9")

    login(client, user_b.username)
    resp = client.get(f"/investigate/graph/data?case_id={case_of_a.id}")
    assert resp.status_code == 403


def test_graph_data_links_tracking_hit_ip_to_ip_investigation(app, client, user_a, case_of_a):
    from app.repositories.investigation_repository import create_investigation

    login(client, user_a.username)
    _seed_link_and_hit(app, user_a, case=case_of_a, ip="203.0.113.77")
    with app.app_context():
        create_investigation(kind="ip", query="203.0.113.77",
                             result_json=json.dumps({"ip": "203.0.113.77", "geo": {}}),
                             user_id=user_a.id, case_id=case_of_a.id, confidence="CONFIRMED")

    resp = client.get(f"/investigate/graph/data?case_id={case_of_a.id}")
    assert resp.status_code == 200
    data = resp.get_json()

    entity_nodes = [n for n in data["nodes"] if n["group"] == "entity_ip" and "203.0.113.77" in n["id"]]
    assert len(entity_nodes) == 1
    entity_edges = [e for e in data["edges"] if e["to"] == entity_nodes[0]["id"]]
    assert len(entity_edges) == 2
