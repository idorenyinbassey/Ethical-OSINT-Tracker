import os
import pytest

from cryptography.fernet import Fernet

# Ensure the encryption key is present for repository operations
os.environ.setdefault("API_KEYS_FERNET_KEY", Fernet.generate_key().decode())

from app.repositories.api_config_repository import (
    create_or_update_config,
    get_by_service,
    delete_config,
)
from app.states.settings_state import SettingsState, API_SERVICES, SUPPORTED_API_SERVICE_KEYS


def test_encrypt_decrypt_roundtrip():
    service = "TEST_ENC"
    try:
        # Save config (this should encrypt the stored key)
        create_or_update_config(
            service_name=service,
            api_key="super-secret-123",
            base_url="https://example.com",
            is_enabled=True,
            rate_limit=10,
            notes="test",
        )

        cfg = get_by_service(service)
        assert cfg is not None
        # After repository read, api_key should be decrypted back to original
        assert cfg.api_key == "super-secret-123"
    finally:
        delete_config(service)


def test_select_service_prefills_free_key_notes():
    state = SettingsState()
    # Use one of the templates we added
    key = "ImageRecognition"
    assert key in API_SERVICES
    state.select_service(key)
    assert state.form_service_name == key
    assert state.form_base_url == API_SERVICES[key]["default_url"]
    # The free_key_notes should be prefilled into form_notes
    assert state.form_notes == API_SERVICES[key].get("free_key_notes", "")


def test_supported_key_list_behaviour():
    assert "WhoisXML" in SUPPORTED_API_SERVICE_KEYS
    assert "ImageRecognition" in SUPPORTED_API_SERVICE_KEYS
    assert "CustomProviderX" not in SUPPORTED_API_SERVICE_KEYS
