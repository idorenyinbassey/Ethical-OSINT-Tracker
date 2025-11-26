from typing import List
from sqlmodel import select
from app.models.api_config import APIConfig
from app.utils.crypto import encrypt_api_key, decrypt_api_key
import json
from app.repositories.base import session_scope


def get_all_configs() -> List[APIConfig]:
    """Get all API configurations"""
    with session_scope(expire_on_commit=False) as session:
        stmt = select(APIConfig).order_by(APIConfig.service_name)
        configs = list(session.exec(stmt))
        # Detach objects from session so they can be used outside
        for config in configs:
            # Decrypt API key before returning to callers
            try:
                config.api_key = decrypt_api_key(config.api_key)
            except Exception:
                pass
            # attempt to parse credentials JSON into an attribute for callers
            try:
                config._credentials = json.loads(config.credentials) if config.credentials else {}
            except Exception:
                config._credentials = {}
            session.expunge(config)
        return configs


def get_by_service(service_name: str) -> APIConfig | None:
    """Get API config by service name"""
    with session_scope(expire_on_commit=False) as session:
        stmt = select(APIConfig).where(APIConfig.service_name == service_name)
        config = session.exec(stmt).first()
        if config:
            try:
                config.api_key = decrypt_api_key(config.api_key)
            except Exception:
                pass
            try:
                config._credentials = json.loads(config.credentials) if config.credentials else {}
            except Exception:
                config._credentials = {}
            session.expunge(config)
        return config


def create_or_update_config(service_name: str, api_key: str, base_url: str, 
                            is_enabled: bool = True, rate_limit: int = 100, 
                            notes: str = "", credentials: dict | None = None) -> APIConfig:
    """Create or update API configuration"""
    with session_scope() as session:
        stmt = select(APIConfig).where(APIConfig.service_name == service_name)
        existing = session.exec(stmt).first()
        
        creds_json = json.dumps(credentials) if credentials else ""
        if existing:
            # Encrypt API key before storing
            try:
                existing.api_key = encrypt_api_key(api_key)
            except Exception:
                existing.api_key = api_key
            existing.base_url = base_url
            existing.is_enabled = is_enabled
            existing.rate_limit = rate_limit
            existing.notes = notes
            existing.credentials = creds_json
            session.add(existing)
            session.flush()
            session.refresh(existing)
            return existing
        else:
            config = APIConfig(
                service_name=service_name,
                api_key=encrypt_api_key(api_key) if api_key else api_key,
                base_url=base_url,
                is_enabled=is_enabled,
                rate_limit=rate_limit,
                notes=notes,
                credentials=creds_json,
            )
            session.add(config)
            session.flush()
            session.refresh(config)
            return config


def delete_config(service_name: str) -> bool:
    """Delete API configuration"""
    with session_scope() as session:
        stmt = select(APIConfig).where(APIConfig.service_name == service_name)
        config = session.exec(stmt).first()
        if config:
            session.delete(config)
            return True
        return False
