"""API key encryption round-trip (Issue #5)."""
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
