"""app.services.tac_lookup — offline IMEI/TAC lookup (free, no API key,
no network). Uses the real bundled database (app/data/tac_database.csv.gz)
since it's a static local file, not an external dependency.

refresh_tac_database() tests isolate the writable path to a tmp_path and
mock get_http_client so they never touch the real network or the real
~/.local/share/osint-tracker, and always invalidate_cache()/restore the
module's writable-path resolution afterward so they can't leak state into
other tests."""
import gzip
import os
import time
import pytest
from unittest.mock import patch
from app.services import tac_lookup


@pytest.fixture(autouse=True)
def _reset_tac_cache():
    tac_lookup.invalidate_cache()
    yield
    tac_lookup.invalidate_cache()


class _FakeResponse:
    def __init__(self, text, status_code=200):
        self.text = text
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")


class _FakeClient:
    def __init__(self, response):
        self._response = response

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def get(self, url, **kwargs):
        return self._response


def _client_factory(response):
    def factory(timeout=30):
        return _FakeClient(response)
    return factory


def _large_valid_csv(extra_row=None):
    rows = ["Brand,TAC,SPECS"]
    if extra_row:
        rows.append(extra_row)
    rows += [f"FILLER,{10_000_000 + i:08d},Filler Phone {i}" for i in range(60_000)]
    return "\n".join(rows) + "\n"


def test_lookup_tac_finds_known_brand():
    result = tac_lookup.lookup_tac("863024073237518")
    assert result["tac"] == "86302407"
    assert result["brand"] == "XIAOMI"
    assert "model" in result
    assert "note" not in result


def test_lookup_tac_reports_unknown_tac():
    result = tac_lookup.lookup_tac("000000001234567")
    assert result["tac"] == "00000000"
    assert "brand" not in result
    assert "note" in result
    # An unmatched TAC must not be mistaken for a confirmed identification
    # by callers (app/routes/investigation.py's imei() confidence check).
    assert result["unverified"] is True


def test_lookup_tac_pads_legacy_short_tac(tmp_path):
    # ~6.6k entries in the real bundled CSV have a leading zero missing
    # (likely stripped by an upstream Excel export) — e.g. a stored 7-digit
    # "1620200" for what should be TAC "01620200". Without zero-padding on
    # load, these rows can never match an IMEI's first-8-digits lookup key.
    writable = tmp_path / "tac_database.csv.gz"
    with gzip.open(writable, mode="wt", encoding="utf-8") as f:
        f.write("Brand,TAC,SPECS\nTCL,1620200,TCL FLIP 2\n")

    with patch.object(tac_lookup, "_writable_db_path", return_value=writable):
        result = tac_lookup.lookup_tac("016202001234567")

    assert result["tac"] == "01620200"
    assert result["brand"] == "TCL"


def test_lookup_tac_strips_non_digits():
    result = tac_lookup.lookup_tac("86-302407 3237518")
    assert result["tac"] == "86302407"
    assert result["brand"] == "XIAOMI"


def test_lookup_tac_sets_imei_only_for_full_length_input():
    short = tac_lookup.lookup_tac("86302407")
    assert short["imei"] is None
    assert "luhn_valid" not in short


def test_luhn_valid_accepts_known_valid_imei():
    # Wikipedia's worked example for the IMEI Luhn check digit.
    assert tac_lookup.luhn_valid("490154203237518") is True


def test_luhn_valid_rejects_tampered_check_digit():
    assert tac_lookup.luhn_valid("490154203237519") is False


# ── Writable-path precedence / fallback ─────────────────────────────────────

def test_load_db_prefers_writable_copy_over_bundled(tmp_path):
    writable = tmp_path / "tac_database.csv.gz"
    with gzip.open(writable, mode="wt", encoding="utf-8") as f:
        f.write("Brand,TAC,SPECS\nSTUBCO,99999999,Stub Phone One\n")

    with patch.object(tac_lookup, "_writable_db_path", return_value=writable):
        result = tac_lookup.lookup_tac("999999991234567")
        assert result["brand"] == "STUBCO"
        # The writable copy is a full replacement, not a merge — a TAC only
        # present in the bundled snapshot won't resolve while it's active.
        bundled_only = tac_lookup.lookup_tac("863024073237518")
        assert "brand" not in bundled_only


def test_load_db_falls_back_to_bundled_when_writable_missing(tmp_path):
    missing = tmp_path / "does-not-exist.csv.gz"
    with patch.object(tac_lookup, "_writable_db_path", return_value=missing):
        result = tac_lookup.lookup_tac("863024073237518")
    assert result["brand"] == "XIAOMI"


def test_load_db_falls_back_to_bundled_when_writable_corrupt(tmp_path):
    corrupt = tmp_path / "tac_database.csv.gz"
    corrupt.write_bytes(b"not actually gzip data")
    with patch.object(tac_lookup, "_writable_db_path", return_value=corrupt):
        result = tac_lookup.lookup_tac("863024073237518")
    assert result["brand"] == "XIAOMI"


# ── refresh_tac_database() ──────────────────────────────────────────────────

def test_refresh_skips_when_disabled_via_env(tmp_path, monkeypatch):
    monkeypatch.setenv("TAC_DB_AUTO_UPDATE", "false")
    target = tmp_path / "tac_database.csv.gz"
    with patch.object(tac_lookup, "_writable_db_path", return_value=target), \
         patch("app.utils.proxy_config.get_http_client") as mock_client:
        assert tac_lookup.refresh_tac_database(min_age_days=0) is False
    mock_client.assert_not_called()


def test_refresh_skips_when_existing_copy_is_recent(tmp_path):
    target = tmp_path / "tac_database.csv.gz"
    with gzip.open(target, mode="wt", encoding="utf-8") as f:
        f.write("Brand,TAC,SPECS\n")

    with patch.object(tac_lookup, "_writable_db_path", return_value=target), \
         patch("app.utils.proxy_config.get_http_client") as mock_client:
        assert tac_lookup.refresh_tac_database(min_age_days=1) is False
    mock_client.assert_not_called()


def test_refresh_rejects_unexpected_header(tmp_path):
    target = tmp_path / "tac_database.csv.gz"
    response = _FakeResponse("Unexpected,Header\nfoo,bar\n")
    with patch.object(tac_lookup, "_writable_db_path", return_value=target), \
         patch("app.utils.proxy_config.get_http_client", _client_factory(response)):
        assert tac_lookup.refresh_tac_database(min_age_days=0) is False
    assert not target.exists()


def test_refresh_rejects_too_few_rows(tmp_path):
    target = tmp_path / "tac_database.csv.gz"
    response = _FakeResponse("Brand,TAC,SPECS\nSTUBCO,99999999,Stub Phone\n")
    with patch.object(tac_lookup, "_writable_db_path", return_value=target), \
         patch("app.utils.proxy_config.get_http_client", _client_factory(response)):
        assert tac_lookup.refresh_tac_database(min_age_days=0) is False
    assert not target.exists()


def test_refresh_success_writes_file_and_invalidates_cache(tmp_path):
    target = tmp_path / "nested" / "tac_database.csv.gz"
    response = _FakeResponse(_large_valid_csv(extra_row="STUBCO,99999999,Stub Phone Two"))

    with patch.object(tac_lookup, "_writable_db_path", return_value=target), \
         patch("app.utils.proxy_config.get_http_client", _client_factory(response)):
        assert tac_lookup.refresh_tac_database(min_age_days=0) is True
        assert target.exists()
        result = tac_lookup.lookup_tac("999999991234567")

    assert result["brand"] == "STUBCO"


def test_refresh_leaves_existing_file_untouched_on_bad_response(tmp_path):
    target = tmp_path / "tac_database.csv.gz"
    with gzip.open(target, mode="wt", encoding="utf-8") as f:
        f.write("Brand,TAC,SPECS\nGOODCO,88888888,Known Good Phone\n")
    # Force refresh_tac_database() past its own "recent copy" skip so the
    # bad-response path is what's actually under test here.
    old_time = time.time() - 2 * 86400
    os.utime(target, (old_time, old_time))

    response = _FakeResponse("garbage, not a csv at all")
    with patch.object(tac_lookup, "_writable_db_path", return_value=target), \
         patch("app.utils.proxy_config.get_http_client", _client_factory(response)):
        assert tac_lookup.refresh_tac_database(min_age_days=1) is False
        result = tac_lookup.lookup_tac("888888881234567")

    assert result["brand"] == "GOODCO"
