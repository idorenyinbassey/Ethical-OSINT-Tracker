"""app.services.typosquat_client — bounded lookalike-domain permutation
generation, DNS resolution, and RDAP enrichment of registered hits only."""
from unittest.mock import patch
from app.services import typosquat_client


def test_generate_permutations_excludes_original_domain():
    perms = typosquat_client._generate_permutations("example.com")
    assert "example.com" not in perms


def test_generate_permutations_capped_at_100():
    perms = typosquat_client._generate_permutations("example.com")
    assert len(perms) <= 100


def test_generate_permutations_deterministic():
    perms1 = typosquat_client._generate_permutations("example.com")
    perms2 = typosquat_client._generate_permutations("example.com")
    assert perms1 == perms2


def test_generate_permutations_includes_tld_swap():
    perms = typosquat_client._generate_permutations("example.com")
    assert "example.net" in perms
    assert "example.org" in perms


def test_generate_permutations_includes_character_omission():
    perms = typosquat_client._generate_permutations("abcd.com")
    assert "bcd.com" in perms  # first char omitted


def test_generate_permutations_includes_duplication():
    perms = typosquat_client._generate_permutations("ab.com")
    assert "aab.com" in perms  # first char duplicated


def test_generate_permutations_includes_homoglyph():
    perms = typosquat_client._generate_permutations("google.com")
    assert "g0ogle.com" in perms  # single-character homoglyph substitution


def test_generate_permutations_no_tld_returns_empty():
    assert typosquat_client._generate_permutations("localhost") == []


def test_resolve_permutation_returns_none_on_gaierror(monkeypatch):
    import socket

    def fake_gethostbyname(host):
        raise socket.gaierror("not registered")

    monkeypatch.setattr(socket, "gethostbyname", fake_gethostbyname)
    assert typosquat_client._resolve_permutation("nope-example.com") is None


def test_resolve_permutation_returns_ip(monkeypatch):
    import socket
    monkeypatch.setattr(socket, "gethostbyname", lambda host: "9.9.9.9")
    result = typosquat_client._resolve_permutation("exampl.com")
    assert result == {"domain": "exampl.com", "ip": "9.9.9.9"}


def test_scan_typosquats_enriches_only_registered_hits():
    domain = "typosquat-test-1.example"
    rdap_calls = []

    def fake_rdap(d):
        rdap_calls.append(d)
        return {"registrar": "Evil Registrar Inc", "created": "2024-01-01"}

    with patch.object(typosquat_client, "_generate_permutations",
                       return_value=["a.example", "b.example", "c.example"]), \
         patch.object(typosquat_client, "_resolve_permutation",
                       side_effect=lambda p: {"domain": p, "ip": "1.2.3.4"} if p == "a.example" else None), \
         patch("app.services.rdap_client.fetch_domain", side_effect=fake_rdap):
        result = typosquat_client.scan_typosquats(domain)

    assert result["permutations_generated"] == 3
    assert result["registered_count"] == 1
    assert result["unregistered_count"] == 2
    assert result["registered"][0]["domain"] == "a.example"
    assert result["registered"][0]["registrar"] == "Evil Registrar Inc"
    assert rdap_calls == ["a.example"]  # RDAP only called for the registered hit


def test_scan_typosquats_no_registered_hits():
    domain = "typosquat-test-2.example"
    with patch.object(typosquat_client, "_generate_permutations", return_value=["a.example"]), \
         patch.object(typosquat_client, "_resolve_permutation", return_value=None):
        result = typosquat_client.scan_typosquats(domain)

    assert result["registered_count"] == 0
    assert result["registered"] == []
    assert result["unregistered_count"] == 1


def test_scan_typosquats_rdap_failure_leaves_registrar_none():
    domain = "typosquat-test-3.example"
    with patch.object(typosquat_client, "_generate_permutations", return_value=["a.example"]), \
         patch.object(typosquat_client, "_resolve_permutation",
                       return_value={"domain": "a.example", "ip": "1.2.3.4"}), \
         patch("app.services.rdap_client.fetch_domain", return_value=None):
        result = typosquat_client.scan_typosquats(domain)

    assert result["registered"][0]["registrar"] is None
    assert result["registered"][0]["created"] is None


def test_scan_typosquats_never_raises_on_internal_error():
    domain = "typosquat-test-4.example"
    with patch.object(typosquat_client, "_generate_permutations", side_effect=RuntimeError("boom")):
        result = typosquat_client.scan_typosquats(domain)

    assert result["domain"] == domain
    assert result["registered"] == []
    assert result["permutations_generated"] == 0
