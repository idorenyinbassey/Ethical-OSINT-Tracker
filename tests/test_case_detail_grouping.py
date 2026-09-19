"""app.routes.cases.detail() groups "Linked Investigations" into
collapsible per-tool-type sections instead of one flat list, so a case
with many scans across many tools stays scannable — the tool-type group
containing the most recently run scan starts open, the rest collapsed."""
import json

from tests.conftest import login


def _seed(app, user_id, case_id, kind, query):
    from app.repositories.investigation_repository import create_investigation
    with app.app_context():
        return create_investigation(
            kind=kind, query=query, result_json=json.dumps({"v": 1}),
            user_id=user_id, case_id=case_id,
        )


def test_detail_groups_investigations_by_kind_with_counts(app, client, user_a, case_of_a):
    login(client, user_a.username)
    _seed(app, user_a.id, case_of_a.id, "social", "johndoe")
    _seed(app, user_a.id, case_of_a.id, "social", "janedoe")
    _seed(app, user_a.id, case_of_a.id, "ip", "8.8.8.8")

    resp = client.get(f"/cases/{case_of_a.id}")
    body = resp.data.decode()
    assert "Social (2)" in body
    assert "Ip (1)" in body


def test_detail_most_recent_kind_group_is_open_by_default(app, client, user_a, case_of_a):
    import re

    login(client, user_a.username)
    _seed(app, user_a.id, case_of_a.id, "ip", "8.8.8.8")
    _seed(app, user_a.id, case_of_a.id, "social", "johndoe")  # run more recently

    resp = client.get(f"/cases/{case_of_a.id}")
    body = resp.data.decode()

    social_details = re.search(r'<details[^>]*>\s*<summary[^>]*>\s*Social', body, re.S)
    ip_details = re.search(r'<details([^>]*)>\s*<summary[^>]*>\s*Ip', body, re.S)
    assert social_details is not None and "open" in social_details.group(0)
    assert ip_details is not None and "open" not in ip_details.group(1)


def test_detail_with_no_investigations_shows_empty_state(app, client, user_a, case_of_a):
    login(client, user_a.username)
    resp = client.get(f"/cases/{case_of_a.id}")
    assert resp.status_code == 200
    assert b"No investigations linked yet." in resp.data
