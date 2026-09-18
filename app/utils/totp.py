"""TOTP 2FA helpers shared between the login flow (app/routes/auth.py) and
the settings enable/disable/regenerate flow (app/routes/settings.py)."""
import hashlib
import json
import secrets
import pyotp
from app.utils.crypto import decrypt_secret

ISSUER_NAME = "Ethical OSINT Tracker"


def generate_secret() -> str:
    return pyotp.random_base32()


def provisioning_uri(secret: str, username: str) -> str:
    return pyotp.totp.TOTP(secret).provisioning_uri(name=username, issuer_name=ISSUER_NAME)


def verify_code(secret: str, code: str) -> bool:
    """Verify a raw TOTP code against a raw (already-decrypted) secret."""
    if not code:
        return False
    try:
        return pyotp.TOTP(secret).verify(code, valid_window=1)
    except Exception:
        return False


def generate_recovery_codes(count: int = 8) -> list[str]:
    """Human-readable one-time recovery codes, e.g. 'ab12-cd34'. Shown to
    the user exactly once — only their hashes are ever stored."""
    codes = []
    for _ in range(count):
        raw = secrets.token_hex(4)
        codes.append(f"{raw[:4]}-{raw[4:]}")
    return codes


def hash_recovery_code(code: str) -> str:
    normalized = code.strip().lower().replace(" ", "")
    return hashlib.sha256(normalized.encode()).hexdigest()


def hash_recovery_codes(codes: list[str]) -> str:
    """JSON-serialize a list of recovery codes as their hashes, ready for
    User.totp_recovery_codes / user_repository.set_recovery_codes."""
    return json.dumps([hash_recovery_code(c) for c in codes])


def verify_totp_or_recovery_code(user, code: str) -> bool:
    """Verify `code` against `user`'s TOTP secret, falling back to
    matching (and consuming — one-time use) a recovery code. Used by the
    login flow's second factor step."""
    if not code:
        return False
    if user.totp_secret:
        try:
            secret = decrypt_secret(user.totp_secret)
            if verify_code(secret, code):
                return True
        except Exception:
            pass
    from app.repositories.user_repository import consume_recovery_code
    return consume_recovery_code(user.id, hash_recovery_code(code))
