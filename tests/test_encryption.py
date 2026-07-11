"""API key encryption round-trip and failure modes (Issue #5)."""
import pytest
from cryptography.fernet import Fernet

from app.utils import crypto
from app.utils.crypto import encrypt_api_key, decrypt_api_key


def test_encrypt_then_decrypt_roundtrip():
    plaintext = "sk-secret-api-key-12345"
    ciphertext = encrypt_api_key(plaintext)
    assert ciphertext != plaintext  # actually encrypted, not passthrough
    assert decrypt_api_key(ciphertext) == plaintext


def test_ciphertext_is_not_readable():
    plaintext = "another-secret-value"
    ciphertext = encrypt_api_key(plaintext)
    assert plaintext not in ciphertext


def test_empty_values_passthrough():
    assert encrypt_api_key("") == ""
    assert decrypt_api_key("") == ""


def test_missing_key_raises_runtime_error(monkeypatch):
    monkeypatch.delenv("API_KEYS_FERNET_KEY", raising=False)
    with pytest.raises(RuntimeError):
        encrypt_api_key("some-value")
    with pytest.raises(RuntimeError):
        decrypt_api_key("some-ciphertext")


def test_wrong_key_fails_to_decrypt(monkeypatch):
    ciphertext = encrypt_api_key("rotate-me")
    # Simulate key rotation: decrypt under a different Fernet key.
    other_key = Fernet.generate_key()
    monkeypatch.setattr(crypto, "_get_fernet_key", lambda: other_key)
    with pytest.raises(RuntimeError):
        decrypt_api_key(ciphertext)


def test_malformed_ciphertext_raises_runtime_error():
    with pytest.raises(RuntimeError):
        decrypt_api_key("this-is-not-valid-fernet-token")


def test_config_roundtrip_through_repository(app):
    from app.repositories.api_config_repository import (
        create_or_update_config, get_by_service, delete_config,
    )
    with app.app_context():
        svc = "_ENC_TEST_"
        try:
            create_or_update_config(
                service_name=svc, api_key="my-live-key", base_url="https://x.example.com",
                is_enabled=True,
            )
            cfg = get_by_service(svc)
            # Repository transparently decrypts on read.
            assert cfg.api_key == "my-live-key"
        finally:
            delete_config(svc)
