"""app.routes.investigation — relationship graph (/investigate/graph/data)
extended to cover the typosquat, paste_leak, and subdomain kinds: shared
entity hub linking (_extract_entities) and typosquat's child-node
expansion (mirroring subdomain's existing pattern)."""
import json
from tests.conftest import login
from app.routes.investigation import _extract_entities


class _FakeInv:
    def __init__(self, id, kind, query):
        self.id = id
        self.kind = kind
        self.query = query


def test_extract_entities_subdomain_registers_domain():
    entity_map = {}
    inv = _FakeInv(1, "subdomain", "example.com")
    _extract_entities(inv, {"domain": "example.com"}, "inv-1", entity_map)
    assert entity_map.get(("domain", "example.com")) == ["inv-1"]


def test_extract_entities_typosquat_registers_domain():
    entity_map = {}
    inv = _FakeInv(2, "typosquat", "example.com")
    _extract_entities(inv, {"domain": "example.com"}, "inv-2", entity_map)
    assert entity_map.get(("domain", "example.com")) == ["inv-2"]


def test_extract_entities_paste_leak_registers_email():
    entity_map = {}
    inv = _FakeInv(3, "paste_leak", "user@example.com")
    _extract_entities(inv, {"query": "user@example.com"}, "inv-3", entity_map)
    assert entity_map.get(("email", "user@example.com")) == ["inv-3"]


def test_extract_entities_paste_leak_registers_domain_for_domain_query():
    entity_map = {}
    inv = _FakeInv(4, "paste_leak", "example.com")
    _extract_entities(inv, {"query": "example.com"}, "inv-4", entity_map)
    assert entity_map.get(("domain", "example.com")) == ["inv-4"]


def test_extract_entities_paste_leak_registers_username_otherwise():
    entity_map = {}
    inv = _FakeInv(5, "paste_leak", "johndoe123")
    _extract_entities(inv, {"query": "johndoe123"}, "inv-5", entity_map)
    assert entity_map.get(("username", "johndoe123")) == ["inv-5"]


# ── Integration: /investigate/graph/data ──────────────────────────────────────

def test_graph_data_expands_typosquat_registered_hits_as_child_nodes(app, client, user_a, case_of_a):
    from app.repositories.investigation_repository import create_investigation

    login(client, user_a.username)
    result = {
        "domain": "example.com",
        "permutations_generated": 10,
        "registered_count": 1,
        "registered": [{"domain": "examp1e.com", "ip": "1.2.3.4", "registrar": "Evil Registrar"}],
    }
    with app.app_context():
        create_investigation(kind="typosquat", query="example.com", result_json=json.dumps(result),
                             user_id=user_a.id, case_id=case_of_a.id, confidence="CONFIRMED")

    resp = client.get("/investigate/graph/data")
    assert resp.status_code == 200
    data = resp.get_json()

    hit_nodes = [n for n in data["nodes"] if n["group"] == "typosquat_hit"]
    assert len(hit_nodes) == 1
    assert "examp1e.com" in hit_nodes[0]["label"]

    typosquat_edges = [e for e in data["edges"] if e["edge_type"] == "typosquat"]
    assert len(typosquat_edges) == 1
    assert typosquat_edges[0]["to"] == hit_nodes[0]["id"]


def test_graph_data_links_shared_domain_between_subdomain_and_typosquat(app, client, user_a, case_of_a):
    from app.repositories.investigation_repository import create_investigation

    login(client, user_a.username)
    with app.app_context():
        create_investigation(kind="subdomain", query="shared-example.com",
                             result_json=json.dumps({"domain": "shared-example.com", "subdomains": []}),
                             user_id=user_a.id, case_id=case_of_a.id, confidence="CONFIRMED")
        create_investigation(kind="typosquat", query="shared-example.com",
                             result_json=json.dumps({"domain": "shared-example.com", "registered": []}),
                             user_id=user_a.id, case_id=case_of_a.id, confidence="CONFIRMED")

    resp = client.get("/investigate/graph/data")
    assert resp.status_code == 200
    data = resp.get_json()

    entity_nodes = [n for n in data["nodes"] if n["group"] == "entity_domain" and "shared-example.com" in n["id"]]
    assert len(entity_nodes) == 1

    entity_edges = [e for e in data["edges"] if e["to"] == entity_nodes[0]["id"]]
    assert len(entity_edges) == 2


def test_graph_data_links_shared_email_between_paste_leak_and_email(app, client, user_a, case_of_a):
    from app.repositories.investigation_repository import create_investigation

    login(client, user_a.username)
    with app.app_context():
        create_investigation(kind="email", query="shared@example.com",
                             result_json=json.dumps({"email": "shared@example.com", "breaches": []}),
                             user_id=user_a.id, case_id=case_of_a.id, confidence="CONFIRMED")
        create_investigation(kind="paste_leak", query="shared@example.com",
                             result_json=json.dumps({"query": "shared@example.com", "pastes": []}),
                             user_id=user_a.id, case_id=case_of_a.id, confidence="CONFIRMED")

    resp = client.get("/investigate/graph/data")
    assert resp.status_code == 200
    data = resp.get_json()

    entity_nodes = [n for n in data["nodes"] if n["group"] == "entity_email" and "shared@example.com" in n["id"]]
    assert len(entity_nodes) == 1

    entity_edges = [e for e in data["edges"] if e["to"] == entity_nodes[0]["id"]]
    assert len(entity_edges) == 2


def test_graph_data_typosquat_with_no_registered_hits_has_no_child_nodes(app, client, user_a, case_of_a):
    from app.repositories.investigation_repository import create_investigation

    login(client, user_a.username)
    with app.app_context():
        create_investigation(kind="typosquat", query="clean-example.com",
                             result_json=json.dumps({"domain": "clean-example.com", "registered": []}),
                             user_id=user_a.id, case_id=case_of_a.id, confidence="UNVERIFIED")

    resp = client.get("/investigate/graph/data")
    assert resp.status_code == 200
    data = resp.get_json()

    hit_nodes = [n for n in data["nodes"] if n["group"] == "typosquat_hit"]
    assert hit_nodes == []
