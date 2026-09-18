"""app.repositories.investigation_repository.find_or_update_recent() —
re-running the same tool/query in the same case, as the same user, must
always update the existing investigation row in place rather than
creating a duplicate sibling, with no time-window limit, and matching
per-user so two different users sharing access to a case don't overwrite
each other's results."""
import json
from datetime import datetime, timedelta

from app.repositories.investigation_repository import (
    find_or_update_recent,
    list_by_case,
)


def test_rerunning_same_query_updates_in_place_not_duplicates(app, user_a, case_of_a):
    with app.app_context():
        first = find_or_update_recent(
            kind="ip", query="8.8.8.8", result_json=json.dumps({"v": 1}),
            user_id=user_a.id, case_id=case_of_a.id,
        )
        second = find_or_update_recent(
            kind="ip", query="8.8.8.8", result_json=json.dumps({"v": 2}),
            user_id=user_a.id, case_id=case_of_a.id,
        )

        rows = list_by_case(case_of_a.id)
        assert len(rows) == 1
        assert second.id == first.id
        assert json.loads(rows[0].result_json) == {"v": 2}


def test_update_has_no_time_window_limit(app, user_a, case_of_a):
    """The old implementation only updated within a 1-hour window and
    created a duplicate after that. The rewritten upsert has no age
    limit at all — simulate an old row by backdating created_at directly
    and confirm a re-run still updates it rather than duplicating."""
    from app.repositories.base import session_scope
    from app.models.investigation import Investigation
    from sqlmodel import select

    with app.app_context():
        first = find_or_update_recent(
            kind="ip", query="8.8.8.8", result_json=json.dumps({"v": 1}),
            user_id=user_a.id, case_id=case_of_a.id,
        )
        with session_scope() as session:
            row = session.exec(select(Investigation).where(Investigation.id == first.id)).one()
            row.created_at = datetime.utcnow() - timedelta(days=30)
            session.add(row)

        find_or_update_recent(
            kind="ip", query="8.8.8.8", result_json=json.dumps({"v": 2}),
            user_id=user_a.id, case_id=case_of_a.id,
        )

        rows = list_by_case(case_of_a.id)
        assert len(rows) == 1
        assert json.loads(rows[0].result_json) == {"v": 2}


def test_different_users_in_same_case_do_not_collide(app, user_a, user_b, case_of_a):
    with app.app_context():
        find_or_update_recent(
            kind="ip", query="8.8.8.8", result_json=json.dumps({"who": "a"}),
            user_id=user_a.id, case_id=case_of_a.id,
        )
        find_or_update_recent(
            kind="ip", query="8.8.8.8", result_json=json.dumps({"who": "b"}),
            user_id=user_b.id, case_id=case_of_a.id,
        )

        rows = list_by_case(case_of_a.id)
        assert len(rows) == 2
        by_user = {r.user_id: json.loads(r.result_json)["who"] for r in rows}
        assert by_user == {user_a.id: "a", user_b.id: "b"}


def test_query_matching_is_case_and_whitespace_insensitive(app, user_a, case_of_a):
    with app.app_context():
        find_or_update_recent(
            kind="domain", query="Example.com", result_json=json.dumps({"v": 1}),
            user_id=user_a.id, case_id=case_of_a.id,
        )
        find_or_update_recent(
            kind="domain", query=" example.com ", result_json=json.dumps({"v": 2}),
            user_id=user_a.id, case_id=case_of_a.id,
        )

        rows = list_by_case(case_of_a.id)
        assert len(rows) == 1
        assert json.loads(rows[0].result_json) == {"v": 2}


def test_different_kind_same_query_does_not_collide(app, user_a, case_of_a):
    with app.app_context():
        find_or_update_recent(
            kind="ip", query="shared-string", result_json=json.dumps({"kind": "ip"}),
            user_id=user_a.id, case_id=case_of_a.id,
        )
        find_or_update_recent(
            kind="domain", query="shared-string", result_json=json.dumps({"kind": "domain"}),
            user_id=user_a.id, case_id=case_of_a.id,
        )

        rows = list_by_case(case_of_a.id)
        assert len(rows) == 2


def test_ad_hoc_investigations_without_a_case_are_never_deduped(app, user_a):
    with app.app_context():
        from app.repositories.investigation_repository import list_all

        find_or_update_recent(
            kind="ip", query="8.8.8.8", result_json=json.dumps({"v": 1}),
            user_id=user_a.id, case_id=None,
        )
        find_or_update_recent(
            kind="ip", query="8.8.8.8", result_json=json.dumps({"v": 2}),
            user_id=user_a.id, case_id=None,
        )

        rows = [r for r in list_all(user_id=user_a.id) if r.case_id is None]
        assert len(rows) == 2


def test_created_at_untouched_but_updated_at_bumped_on_refresh(app, user_a, case_of_a):
    with app.app_context():
        first = find_or_update_recent(
            kind="ip", query="8.8.8.8", result_json=json.dumps({"v": 1}),
            user_id=user_a.id, case_id=case_of_a.id,
        )
        second = find_or_update_recent(
            kind="ip", query="8.8.8.8", result_json=json.dumps({"v": 2}),
            user_id=user_a.id, case_id=case_of_a.id,
        )

        assert second.created_at == first.created_at
        assert second.updated_at is not None


def test_plugin_run_route_updates_in_place_instead_of_duplicating(app, client, user_a, case_of_a):
    from tests.conftest import login
    from app.plugins import get_all

    plugins = get_all()
    if not plugins:
        import pytest
        pytest.skip("no plugins registered")
    plugin_name = plugins[0].name

    login(client, user_a.username)
    for _ in range(2):
        resp = client.post(
            f"/investigate/plugins/{plugin_name}",
            data={"query": "same-query", "case_id": str(case_of_a.id)},
        )
        assert resp.status_code in (200, 302)

    with app.app_context():
        rows = [r for r in list_by_case(case_of_a.id) if r.kind == f"plugin_{plugin_name}"]
        assert len(rows) == 1
