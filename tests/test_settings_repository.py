"""Tests for api_config_repository and settings service list."""
import pytest
from app import create_app
from app.db import init_db
from app.repositories.api_config_repository import (
    create_or_update_config,
    get_by_service,
    get_all_configs,
    delete_config,
)
from app.routes.settings import SERVICES


@pytest.fixture(scope="module")
def app_ctx():
    app = create_app()
    app.config["TESTING"] = True
    with app.app_context():
        init_db()
        yield app


def test_create_and_retrieve_config(app_ctx):
    service = "_TEST_SVC_"
    try:
        create_or_update_config(
            service_name=service,
            api_key="test-key-abc",
            base_url="https://test.example.com",
            is_enabled=True,
            notes="unit test",
        )
        cfg = get_by_service(service)
        assert cfg is not None
        assert cfg.api_key == "test-key-abc"
        assert cfg.base_url == "https://test.example.com"
        assert cfg.is_enabled is True
        assert cfg.notes == "unit test"
    finally:
        delete_config(service)


def test_update_existing_config(app_ctx):
    service = "_TEST_UPDATE_"
    try:
        create_or_update_config(service_name=service, api_key="v1", base_url="https://a.com", is_enabled=False)
        create_or_update_config(service_name=service, api_key="v2", base_url="https://b.com", is_enabled=True)
        cfg = get_by_service(service)
        assert cfg.api_key == "v2"
        assert cfg.base_url == "https://b.com"
        assert cfg.is_enabled is True
    finally:
        delete_config(service)


def test_delete_config(app_ctx):
    service = "_TEST_DEL_"
    create_or_update_config(service_name=service, api_key="x", base_url="", is_enabled=False)
    assert get_by_service(service) is not None
    delete_config(service)
    assert get_by_service(service) is None


def test_get_nonexistent_returns_none(app_ctx):
    cfg = get_by_service("_NONEXISTENT_SERVICE_XYZ_")
    assert cfg is None


def test_services_list_has_expected_keys(app_ctx):
    names = {s["name"] for s in SERVICES}
    assert "Shodan" in names
    assert "VirusTotal" in names
    assert "HIBP" in names
    assert "ImageRecognition" in names
    assert "TorProxy" in names
    # Removed in Flask rewrite
    assert "SocialSearch" not in names


def test_services_list_has_default_urls(app_ctx):
    for svc in SERVICES:
        assert "name" in svc
        assert "label" in svc
        assert "default_url" in svc


def test_all_configs_returns_list(app_ctx):
    configs = get_all_configs()
    assert isinstance(configs, list)
