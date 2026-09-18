"""app.services.tac_lookup — offline IMEI/TAC lookup (free, no API key,
no network). Uses the real bundled database (app/data/tac_database.csv.gz)
since it's a static local file, not an external dependency."""
from app.services import tac_lookup


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
