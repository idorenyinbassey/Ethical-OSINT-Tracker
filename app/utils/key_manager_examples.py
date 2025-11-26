"""Example backends for `app.utils.key_manager`.

These are lightweight examples showing how to implement a backend for
HashiCorp Vault and AWS KMS. They are intentionally dependency-free
stubs: if you want to enable them, install the appropriate SDKs and
replace the `NotImplementedError` sections with real calls.

Do NOT enable these in production without adding proper auth and
error handling.
"""
from typing import Optional

class VaultBackend:
    """Example Vault backend (requires `hvac` library).

    Usage:
        from app.utils.key_manager import key_manager
        vault = VaultBackend(url="https://vault:8200", token="...", mount="secret")
        key_manager.backend = vault
    """

    def __init__(self, url: str, token: str, mount: str = "secret") -> None:
        self.url = url
        self.token = token
        self.mount = mount

    def get(self, name: str) -> Optional[str]:
        # Implement using hvac.Client(token=...) and client.secrets.kv.v2.read_secret_version
        raise NotImplementedError("Install 'hvac' and implement VaultBackend.get()")

    def set(self, name: str, value: str) -> None:
        # Implement using client.secrets.kv.v2.create_or_update_secret
        raise NotImplementedError("Install 'hvac' and implement VaultBackend.set()")


class AWSKMSBackend:
    """Example AWS KMS backend (requires `boto3`).

    This example would typically store the ciphertext in SSM or Secrets
    Manager and use KMS to encrypt/decrypt, or use KMS directly to
    generate data keys. For brevity this is a stub.
    """

    def __init__(self, region: str):
        self.region = region

    def get(self, name: str) -> Optional[str]:
        raise NotImplementedError("Install 'boto3' and implement AWSKMSBackend.get()")

    def set(self, name: str, value: str) -> None:
        raise NotImplementedError("Install 'boto3' and implement AWSKMSBackend.set()")
