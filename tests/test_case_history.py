"""A case's own tool history, shown right on each tool's page.

Covers `list_by_case_and_kind()` (app/repositories/investigation_repository.py)
and the shared `_resolve_case_context()` route helper (app/routes/investigation.py)
that every tool route now goes through: GET with `?case_id=X` shows that
case's past results for this tool with no search run, POST shows the new
result plus history excluding it, and a case_id for a case the requester
can't access is rejected on both GET and POST — closing a previously-latent
gap where case_id was only ever read from POST with no access check at all.
"""
import json
from unittest.mock import patch

from tests.conftest import login


def _seed(app, user_id, case_id, kind, query, result=None):
    from app.repositories.investigation_repository import create_investigation
    with app.app_context():
        return create_investigation(
            kind=kind, query=query, result_json=json.dumps(result or {"v": 1}),
            user_id=user_id, case_id=case_id, confidence="CONFIRMED",
        )


# ── list_by_case_and_kind() ─────────────────────────────────────────────────

def test_list_by_case_and_kind_filters_by_both(app, user_a, case_of_a):
    from app.repositories.investigation_repository import list_by_case_and_kind

    _seed(app, user_a.id, case_of_a.id, "social", "alice")
    _seed(app, user_a.id, case_of_a.id, "ip", "8.8.8.8")

    with app.app_context():
        rows = list_by_case_and_kind(case_of_a.id, "social")
        assert [r.kind for r in rows] == ["social"]


def test_list_by_case_and_kind_excludes_given_id(app, user_a, case_of_a):
    from app.repositories.investigation_repository import list_by_case_and_kind

    first = _seed(app, user_a.id, case_of_a.id, "social", "alice")
    second = _seed(app, user_a.id, case_of_a.id, "social", "bob")

    with app.app_context():
        rows = list_by_case_and_kind(case_of_a.id, "social", exclude_id=second.id)
        assert [r.id for r in rows] == [first.id]


def test_list_by_case_and_kind_orders_newest_first(app, user_a, case_of_a):
    from app.repositories.base import session_scope
    from app.models.investigation import Investigation
    from app.repositories.investigation_repository import list_by_case_and_kind
    from sqlmodel import select
    from datetime import datetime, timedelta

    older = _seed(app, user_a.id, case_of_a.id, "social", "alice")
    newer = _seed(app, user_a.id, case_of_a.id, "social", "bob")
    with app.app_context():
        with session_scope() as session:
            row = session.exec(select(Investigation).where(Investigation.id == older.id)).one()
            row.created_at = datetime.utcnow() - timedelta(days=1)
            session.add(row)

        rows = list_by_case_and_kind(case_of_a.id, "social")
        assert [r.id for r in rows] == [newer.id, older.id]


def test_list_by_case_and_kind_does_not_leak_another_case(app, user_a, case_of_a):
    from app.repositories.case_repository import create_case
    from app.repositories.investigation_repository import list_by_case_and_kind

    with app.app_context():
        other_case = create_case("Other Case", "", owner_user_id=user_a.id)
    _seed(app, user_a.id, case_of_a.id, "social", "alice")
    _seed(app, user_a.id, other_case.id, "social", "carol")

    with app.app_context():
        rows = list_by_case_and_kind(case_of_a.id, "social")
        assert [r.query for r in rows] == ["alice"]


# ── social() route ───────────────────────────────────────────────────────────

def test_social_get_with_case_id_shows_history_without_running_search(app, client, user_a, case_of_a):
    inv = _seed(app, user_a.id, case_of_a.id, "social", "alice", {"username": "alice"})
    login(client, user_a.username)

    resp = client.get(f"/investigate/social?case_id={case_of_a.id}")
    assert resp.status_code == 200
    body = resp.data.decode()
    assert "alice" in body
    assert "Previous results in this case" in body


def test_social_post_shows_new_result_plus_history_excluding_it(app, client, user_a, case_of_a):
    _seed(app, user_a.id, case_of_a.id, "social", "alice", {"username": "alice"})
    login(client, user_a.username)

    fake_result = {"username": "bob", "found_count": 0, "confirmed_count": 0, "total_checked": 0, "results": []}
    with patch("app.routes.investigation.social_client.search_username", return_value=fake_result):
        resp = client.post(
            "/investigate/social",
            data={"query": "bob", "case_id": str(case_of_a.id)},
        )
    assert resp.status_code == 200
    body = resp.data.decode()
    assert "Previous results in this case (1)" in body
    assert "alice" in body


def test_social_case_id_for_inaccessible_case_rejected_on_get(app, client, user_a, user_b, case_of_a):
    from app.repositories.case_repository import create_case

    with app.app_context():
        create_case("Case B", "owned by B", owner_user_id=user_b.id)
    login(client, user_b.username)
    resp = client.get(f"/investigate/social?case_id={case_of_a.id}")
    assert resp.status_code == 403


def test_social_case_id_for_inaccessible_case_rejected_on_post(app, client, user_a, user_b, case_of_a):
    from app.repositories.case_repository import create_case

    with app.app_context():
        create_case("Case B", "owned by B", owner_user_id=user_b.id)
    login(client, user_b.username)

    resp = client.post(
        "/investigate/social",
        data={"query": "bob", "case_id": str(case_of_a.id)},
    )
    assert resp.status_code == 403


# ── company() route ──────────────────────────────────────────────────────────

def test_company_get_with_case_id_shows_history_without_running_search(app, client, user_a, case_of_a):
    _seed(app, user_a.id, case_of_a.id, "company", "Acme Corp", {"query": "Acme Corp"})
    login(client, user_a.username)

    resp = client.get(f"/investigate/company?case_id={case_of_a.id}")
    assert resp.status_code == 200
    body = resp.data.decode()
    assert "Acme Corp" in body
    assert "Previous results in this case" in body


def test_company_post_shows_new_result_plus_history_excluding_it(app, client, user_a, case_of_a):
    _seed(app, user_a.id, case_of_a.id, "company", "Acme Corp", {"query": "Acme Corp"})
    login(client, user_a.username)

    empty_registry = {"source": "", "found": False}
    fake_result = {
        "query": "Globex",
        "results": {
            "us_edgar": dict(empty_registry, source="US EDGAR"),
            "uk": dict(empty_registry, source="UK Companies House"),
            "nigeria": dict(empty_registry, source="CAC Nigeria"),
            "canada": dict(empty_registry, source="Corporations Canada"),
            "cyprus": dict(empty_registry, source="Cyprus DRCOR"),
            "duckduckgo": {"found": False},
            "google_dorks": {"links": []},
        },
    }
    with patch("app.services.company_client.search_companies", return_value=fake_result):
        resp = client.post(
            "/investigate/company",
            data={"query": "Globex", "case_id": str(case_of_a.id)},
        )
    assert resp.status_code == 200
    body = resp.data.decode()
    assert "Previous results in this case (1)" in body
    assert "Acme Corp" in body


def test_company_case_id_for_inaccessible_case_rejected_on_get(app, client, user_a, user_b, case_of_a):
    from app.repositories.case_repository import create_case

    with app.app_context():
        create_case("Case B", "owned by B", owner_user_id=user_b.id)
    login(client, user_b.username)
    resp = client.get(f"/investigate/company?case_id={case_of_a.id}")
    assert resp.status_code == 403


def test_company_case_id_for_inaccessible_case_rejected_on_post(app, client, user_a, user_b, case_of_a):
    from app.repositories.case_repository import create_case

    with app.app_context():
        create_case("Case B", "owned by B", owner_user_id=user_b.id)
    login(client, user_b.username)

    resp = client.post(
        "/investigate/company",
        data={"query": "Globex", "case_id": str(case_of_a.id)},
    )
    assert resp.status_code == 403


# ── smoke check across a few more tool pages ────────────────────────────────

def test_ip_page_renders_with_history_present(app, client, user_a, case_of_a):
    _seed(app, user_a.id, case_of_a.id, "ip", "8.8.8.8", {"geo": {"city": "Mountain View"}})
    login(client, user_a.username)

    resp = client.get(f"/investigate/ip?case_id={case_of_a.id}")
    assert resp.status_code == 200
    assert "8.8.8.8" in resp.data.decode()


def test_breach_page_renders_with_history_present(app, client, user_a, case_of_a):
    _seed(app, user_a.id, case_of_a.id, "breach", "user@example.com", {"breaches": []})
    login(client, user_a.username)

    resp = client.get(f"/investigate/breach?case_id={case_of_a.id}")
    assert resp.status_code == 200
    assert "Previous results in this case" in resp.data.decode()


def test_vehicle_page_renders_with_history_present(app, client, user_a, case_of_a):
    _seed(app, user_a.id, case_of_a.id, "vehicle", "1HGBH41JXMN109186", {"summary": {"make": "Honda"}})
    login(client, user_a.username)

    resp = client.get(f"/investigate/vehicle?case_id={case_of_a.id}")
    assert resp.status_code == 200
    assert "Previous results in this case" in resp.data.decode()


def test_file_forensics_page_renders_with_history_present(app, client, user_a, case_of_a):
    _seed(app, user_a.id, case_of_a.id, "file_forensics", "photo.jpg", {"file_name": "photo.jpg"})
    login(client, user_a.username)

    resp = client.get(f"/investigate/file?case_id={case_of_a.id}")
    assert resp.status_code == 200
    assert "Previous results in this case" in resp.data.decode()


def test_no_case_selected_shows_no_history_section(app, client, user_a, case_of_a):
    """No case_id at all → no history query, no section rendered."""
    _seed(app, user_a.id, case_of_a.id, "ip", "8.8.8.8")
    login(client, user_a.username)

    resp = client.get("/investigate/ip")
    assert resp.status_code == 200
    assert "Previous results in this case" not in resp.data.decode()
