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
    """Return a Fernet instance or None if cryptography unavailable."""
    if Fernet is None:
        return None
    key = os.environ.get("API_KEYS_FERNET_KEY")
    if key:
        return Fernet(key.encode())
    # Try local key file for dev convenience
    key_file = Path(".api_keys_key")
    if key_file.exists():
        k = key_file.read_text().strip()
        return Fernet(k.encode())
    # Generate and persist a local key for development
    k = Fernet.generate_key()
    try:
        key_file.write_text(k.decode())
    except Exception:
        pass
    return Fernet(k)


def encrypt_api_key(plaintext: str) -> str:
    """Encrypt API key using Fernet. Returns ciphertext or plaintext on fallback."""
    f = _get_fernet()
    if f is None:
        return plaintext
    return f.encrypt(plaintext.encode()).decode()


def decrypt_api_key(ciphertext: str) -> str:
    """Decrypt API key using Fernet. If decryption fails, return original value."""
    f = _get_fernet()
    if f is None:
        return ciphertext
    try:
        return f.decrypt(ciphertext.encode()).decode()
    except Exception:
        return ciphertext
