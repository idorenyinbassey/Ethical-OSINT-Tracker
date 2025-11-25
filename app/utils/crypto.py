"""Helpers for hashing and encrypting sensitive values.

This module exposes simple hashing helpers for identifiers and a
lightweight Fernet-based encryption/decryption helper for API keys.
Encryption uses the `API_KEYS_FERNET_KEY` env var when available, or
falls back to a local key file `.api_keys_key` for development.
"""
import hashlib
import os
from pathlib import Path
from typing import Optional

try:
    from cryptography.fernet import Fernet
except Exception:  # pragma: no cover - cryptography may be missing in some envs
    Fernet = None  # type: ignore


def hash_identifier(value: str) -> str:
    """Hash sensitive identifier (email, phone) using SHA256."""
    return hashlib.sha256(value.encode()).hexdigest()


def hash_if_sensitive(kind: str, query: str) -> str:
    """Hash query if it's a sensitive resource type."""
    sensitive_kinds = {"email", "phone"}
    if kind in sensitive_kinds:
        return hash_identifier(query)
    return query


def _get_fernet() -> Optional["Fernet"]:
    """Return a Fernet instance if `API_KEYS_FERNET_KEY` env var is set.

    This function enforces the use of an explicit environment variable
    for encryption keys. It will return None if either `cryptography` is
    unavailable or `API_KEYS_FERNET_KEY` is not set.
    """
    if Fernet is None:
        return None
    key = os.environ.get("API_KEYS_FERNET_KEY")
    if not key:
        return None
    return Fernet(key.encode())


def encrypt_api_key(plaintext: str) -> str:
    """Encrypt API key using Fernet. Raises RuntimeError if no env key set."""
    f = _get_fernet()
    if f is None:
        raise RuntimeError("API_KEYS_FERNET_KEY is not set or cryptography is unavailable")
    return f.encrypt(plaintext.encode()).decode()


def decrypt_api_key(ciphertext: str) -> str:
    """Decrypt API key using Fernet. Raises RuntimeError if no env key set.

    If decryption fails (invalid token) the original ciphertext is
    returned to avoid data loss, but a RuntimeError is raised if the
    environment is not configured for encryption.
    """
    f = _get_fernet()
    if f is None:
        raise RuntimeError("API_KEYS_FERNET_KEY is not set or cryptography is unavailable")
    try:
        return f.decrypt(ciphertext.encode()).decode()
    except Exception:
        return ciphertext
