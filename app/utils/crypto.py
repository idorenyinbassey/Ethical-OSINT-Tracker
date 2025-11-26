"""Helpers for hashing identifiers and simple API key passthrough.

This project previously encrypted API keys using Fernet. To simplify
local setup and CI, encryption has been removed: `encrypt_api_key`
and `decrypt_api_key` are now no-op passthroughs that return the
input string unchanged.
"""
import hashlib


def hash_identifier(value: str) -> str:
    """Hash sensitive identifier (email, phone) using SHA256."""
    return hashlib.sha256(value.encode()).hexdigest()


def hash_if_sensitive(kind: str, query: str) -> str:
    """Hash query if it's a sensitive resource type."""
    sensitive_kinds = {"email", "phone"}
    if kind in sensitive_kinds:
        return hash_identifier(query)
    return query


def encrypt_api_key(plaintext: str) -> str:
    """Passthrough: return API key unchanged (no encryption)."""
    return plaintext


def decrypt_api_key(ciphertext: str) -> str:
    """Passthrough: return stored API key unchanged (no encryption)."""
    return ciphertext
