"""Cryptographic helpers for sensitive data: API key encryption and identifier hashing."""
import hashlib
import os
from cryptography.fernet import Fernet, InvalidToken


def hash_identifier(value: str) -> str:
    """Hash sensitive identifier (email, phone) using SHA256."""
    return hashlib.sha256(value.encode()).hexdigest()


def hash_if_sensitive(kind: str, query: str) -> str:
    """Hash query if it's a sensitive resource type."""
    sensitive_kinds = {"email", "phone"}
    if kind in sensitive_kinds:
        return hash_identifier(query)
    return query


def _get_fernet_key() -> bytes:
    """Get Fernet encryption key from environment variable.

    Raises RuntimeError if key is not set (required for secure operation).
    """
    key_str = os.getenv("API_KEYS_FERNET_KEY")
    if not key_str:
        raise RuntimeError(
            "API_KEYS_FERNET_KEY environment variable not set. "
            "API keys cannot be stored securely. "
            "Set this to a valid Fernet key from cryptography.fernet.Fernet.generate_key(). "
            "For development, generate one with: python -c \"from cryptography.fernet import Fernet; "
            "print(Fernet.generate_key().decode())\""
        )
    return key_str.encode() if isinstance(key_str, str) else key_str


def encrypt_api_key(plaintext: str) -> str:
    """Encrypt API key using Fernet symmetric encryption.

    Args:
        plaintext: The unencrypted API key

    Returns:
        URL-safe base64 encoded encrypted key (can be safely stored in database)

    Raises:
        RuntimeError: If encryption key is not configured
    """
    if not plaintext:
        return plaintext

    try:
        key = _get_fernet_key()
        cipher = Fernet(key)
        encrypted = cipher.encrypt(plaintext.encode())
        return encrypted.decode()  # Return as string for database storage
    except RuntimeError:
        raise
    except Exception as e:
        raise RuntimeError(f"Failed to encrypt API key: {e}") from e


def decrypt_api_key(ciphertext: str) -> str:
    """Decrypt API key using Fernet symmetric encryption.

    Args:
        ciphertext: The encrypted API key (from database)

    Returns:
        The decrypted API key

    Raises:
        RuntimeError: If decryption fails (key mismatch, invalid token, etc.)
    """
    if not ciphertext:
        return ciphertext

    try:
        key = _get_fernet_key()
        cipher = Fernet(key)
        decrypted = cipher.decrypt(ciphertext.encode())
        return decrypted.decode()
    except InvalidToken:
        raise RuntimeError(
            "Failed to decrypt API key: Invalid token. "
            "This usually means the encryption key has changed. "
            "Existing encrypted keys cannot be decrypted with a different key."
        ) from None
    except RuntimeError:
        raise
    except Exception as e:
        raise RuntimeError(f"Failed to decrypt API key: {e}") from e
