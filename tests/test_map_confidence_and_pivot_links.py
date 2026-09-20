"""Part C: map markers carry a confidence tier (exact/approximate/
suspected), Company Registry addresses are geocoded into "suspected"
markers, and an extracted email/IP/domain/phone value in the scan
viewer / tool history offers an "Investigate with X ->" pivot link that
lands on the target tool with the value prefilled."""
import json
from unittest.mock import patch

from tests.conftest import login


def _seed(app, user_id, case_id, kind, query, result):
    from app.repositories.investigation_repository import create_investigation
    with app.app_context():
        return create_investigation(
            kind=kind, query=query, result_json=json.dumps(result),
            user_id=user_id, case_id=case_id, confidence="CONFIRMED",
        )


# ── Map confidence tiers ─────────────────────────────────────────────────────

def test_ip_marker_is_approximate_confidence(app, client, user_a, case_of_a):
    _seed(app, user_a.id, case_of_a.id, "ip", "8.8.8.8",
          {"geo": {"lat": 37.4, "lon": -122.08, "city": "Mountain View"}})
    login(client, user_a.username)

    resp = client.get(f"/investigate/map/data?case_id={case_of_a.id}")
    markers = resp.get_json()["markers"]
    assert len(markers) == 1
    assert markers[0]["confidence"] == "approximate"


def test_file_forensics_marker_is_exact_confidence(app, client, user_a, case_of_a):
    _seed(app, user_a.id, case_of_a.id, "file_forensics", "photo.jpg",
          {"metadata": {"GPS_Coordinates": "37.4, -122.08"}})
    login(client, user_a.username)

    resp = client.get(f"/investigate/map/data?case_id={case_of_a.id}")
    markers = resp.get_json()["markers"]
    assert len(markers) == 1
    assert markers[0]["confidence"] == "exact"


def test_company_address_geocoded_into_suspected_marker(app, client, user_a, case_of_a):
    from app.services import geocode_client

    _seed(app, user_a.id, case_of_a.id, "company", "Acme Corp", {
        "query": "Acme Corp",
        "results": {"uk": {"found": [{"name": "Acme Corp Ltd", "address": "1 Example Street, London"}]}},
    })
    login(client, user_a.username)

    fake_geocode = {"lat": 51.5, "lon": -0.1, "display_name": "1 Example Street, London, UK"}
    with patch.object(geocode_client, "geocode", return_value=fake_geocode) as mock_geocode:
        resp = client.get(f"/investigate/map/data?case_id={case_of_a.id}")

    mock_geocode.assert_called_once_with("1 Example Street, London")
    markers = resp.get_json()["markers"]
    assert len(markers) == 1
    assert markers[0]["confidence"] == "suspected"
    assert markers[0]["lat"] == 51.5
    assert markers[0]["label"] == "Acme Corp Ltd"


def test_company_address_geocoded_regardless_of_which_registry_key(app, client, user_a, case_of_a):
    """map_data()'s company-address geocoding loop is generalized to scan
    every registry key in results, not just "uk" — this seeds a hit under
    "nigeria" (added once the CAC switch surfaced an address field) to
    confirm it geocodes identically."""
    from app.services import geocode_client

    _seed(app, user_a.id, case_of_a.id, "company", "Acme Nigeria", {
        "query": "Acme Nigeria",
        "results": {"nigeria": {"found": [{"name": "Acme Nigeria Ltd", "address": "1 Lagos Street"}]}},
    })
    login(client, user_a.username)

    fake_geocode = {"lat": 6.5, "lon": 3.4, "display_name": "1 Lagos Street, Lagos, Nigeria"}
    with patch.object(geocode_client, "geocode", return_value=fake_geocode) as mock_geocode:
        resp = client.get(f"/investigate/map/data?case_id={case_of_a.id}")

    mock_geocode.assert_called_once_with("1 Lagos Street")
    markers = resp.get_json()["markers"]
    assert len(markers) == 1
    assert markers[0]["confidence"] == "suspected"
    assert markers[0]["label"] == "Acme Nigeria Ltd"


def test_company_with_no_address_produces_no_marker(app, client, user_a, case_of_a):
    from app.services import geocode_client

    _seed(app, user_a.id, case_of_a.id, "company", "No Address Co", {
        "query": "No Address Co",
        "results": {"uk": {"found": [{"name": "No Address Co Ltd"}]}},
    })
    login(client, user_a.username)

    with patch.object(geocode_client, "geocode") as mock_geocode:
        resp = client.get(f"/investigate/map/data?case_id={case_of_a.id}")

    mock_geocode.assert_not_called()
    assert resp.get_json()["markers"] == []


def test_company_geocoding_capped_at_three_hits(app, client, user_a, case_of_a):
    from app.services import geocode_client

    hits = [{"name": f"Co {i}", "address": f"{i} Example Street"} for i in range(5)]
    _seed(app, user_a.id, case_of_a.id, "company", "Many Hits Co", {
        "query": "Many Hits Co", "results": {"uk": {"found": hits}},
    })
    login(client, user_a.username)

    with patch.object(geocode_client, "geocode", return_value={"lat": 1.0, "lon": 2.0, "display_name": "x"}) as mock_geocode:
        client.get(f"/investigate/map/data?case_id={case_of_a.id}")

    assert mock_geocode.call_count == 3


# ── Pivot links ("Investigate this value with X ->") ────────────────────────

def test_case_scan_viewer_shows_pivot_link_for_extracted_email(app, client, user_a, case_of_a):
    inv = _seed(app, user_a.id, case_of_a.id, "domain", "example.com",
               {"registrant_email": "admin@example.com"})
    login(client, user_a.username)

    resp = client.get(f"/cases/{case_of_a.id}/investigations/{inv.id}")
    body = resp.data.decode()
    assert "Investigate with Email Analysis" in body
    assert "/investigate/email?" in body
    assert "query=admin" in body
    assert f"case_id={case_of_a.id}" in body


def test_case_scan_viewer_shows_pivot_link_for_extracted_ip(app, client, user_a, case_of_a):
    inv = _seed(app, user_a.id, case_of_a.id, "email_header", "phish@example.com",
               {"x_originating_ip": "203.0.113.5"})
    login(client, user_a.username)

    resp = client.get(f"/cases/{case_of_a.id}/investigations/{inv.id}")
    body = resp.data.decode()
    assert "Investigate with IP Lookup" in body
    assert "query=203.0.113.5" in body


def test_pivot_link_does_not_appear_for_a_plain_non_entity_value(app, client, user_a, case_of_a):
    inv = _seed(app, user_a.id, case_of_a.id, "ip", "8.8.8.8", {"status": "active", "count": 3})
    login(client, user_a.username)

    resp = client.get(f"/cases/{case_of_a.id}/investigations/{inv.id}")
    assert b"Investigate with" not in resp.data


def test_tool_history_section_also_shows_pivot_link(app, client, user_a, case_of_a):
    _seed(app, user_a.id, case_of_a.id, "domain", "example.com",
          {"registrant_email": "admin@example.com"})
    login(client, user_a.username)

    resp = client.get(f"/investigate/domain?case_id={case_of_a.id}")
    assert b"Investigate with Email Analysis" in resp.data


def test_investigate_email_prefills_query_from_get_param(client, user_a, case_of_a):
    login(client, user_a.username)
    resp = client.get(f"/investigate/email?query=someone%40example.com&case_id={case_of_a.id}")
    assert resp.status_code == 200
    assert b'value="someone@example.com"' in resp.data


def test_investigate_ip_prefills_query_from_get_param(client, user_a, case_of_a):
    login(client, user_a.username)
    resp = client.get("/investigate/ip?query=8.8.4.4")
    assert resp.status_code == 200
    assert b'value="8.8.4.4"' in resp.data
