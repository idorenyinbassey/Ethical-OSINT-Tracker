"""Pluggable key manager interface for production key storage.

This module provides a minimal, dependency-free interface for storing
and retrieving secrets (API keys). It intentionally does NOT ship a
production KMS integration by default — instead it offers simple
adapters that you can implement and wire in (HashiCorp Vault, AWS
KMS, Google KMS, Azure Key Vault, etc.).

Usage:
    from app.utils.key_manager import key_manager
    key_manager.set("API_KEYS_FERNET_KEY", "secret-value")
    key = key_manager.get("API_KEYS_FERNET_KEY")

The default implementation reads from environment variables and an
in-memory store. Replace with a Vault/KMS-backed implementation in
production by assigning `key_manager.backend = YourBackend()`.
"""
from typing import Optional, Dict
import os


class KeyBackend:
    """Abstract backend interface."""

    def get(self, name: str) -> Optional[str]:
        raise NotImplementedError()

    def set(self, name: str, value: str) -> None:
        raise NotImplementedError()


class EnvBackend(KeyBackend):
    """Read-only backend backed by environment variables."""

    def get(self, name: str) -> Optional[str]:
        return os.environ.get(name)

    def set(self, name: str, value: str) -> None:
        # Intentionally no-op: do not write to process env for persistence
        raise RuntimeError("EnvBackend is read-only")


class MemoryBackend(KeyBackend):
    """Simple in-memory backend for local use and tests."""

    def __init__(self) -> None:
        self._store: Dict[str, str] = {}

    def get(self, name: str) -> Optional[str]:
        return self._store.get(name)

    def set(self, name: str, value: str) -> None:
        self._store[name] = value


# Global key_manager instance with default backends: env first, then memory
class KeyManager:
    def __init__(self) -> None:
        self.env = EnvBackend()
        self.memory = MemoryBackend()
        self.backend: KeyBackend = self.env

    def get(self, name: str) -> Optional[str]:
        # Try selected backend first, fall back to environment
        val = None
        try:
            val = self.backend.get(name)
        except Exception:
            val = None
        if val is None:
            return self.env.get(name) or self.memory.get(name)
        return val

    def set(self, name: str, value: str) -> None:
        # Default behavior: write to memory backend
        try:
            self.backend.set(name, value)
        except Exception:
            self.memory.set(name, value)


key_manager = KeyManager()


__all__ = ["KeyManager", "KeyBackend", "EnvBackend", "MemoryBackend", "key_manager"]
