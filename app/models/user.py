import datetime
from sqlmodel import SQLModel, Field
from flask_login import UserMixin


class User(UserMixin, SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    password_hash: str
    created_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.utcnow())
    is_active: bool = Field(default=True, sa_column_kwargs={"name": "is_active"})
    is_admin: bool = Field(default=False)
    # TOTP 2FA. totp_secret is Fernet-encrypted (app.utils.crypto.encrypt_secret)
    # using the same key as everything else in app.utils.crypto — never stored
    # in plaintext. totp_recovery_codes is a JSON array of SHA-256-hashed
    # one-time codes (same hashing rationale as API keys: high-entropy random
    # tokens, not passwords — see app/models/api_key.py).
    totp_secret: str | None = Field(default=None)
    totp_enabled: bool = Field(default=False)
    totp_recovery_codes: str = Field(default="")

    def get_id(self) -> str:
        return str(self.id)

    @property
    def active(self) -> bool:
        return self.is_active
