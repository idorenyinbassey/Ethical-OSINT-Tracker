from sqlmodel import SQLModel, Field
from typing import Optional
import datetime


class ApiKey(SQLModel, table=True):
    """A user-issued API key for the /api/v1 REST surface.

    Distinct from app.models.api_config.APIConfig, which stores THIRD-PARTY
    service credentials (Shodan, VirusTotal, etc.) — this is a key *this app*
    issues to a user so external tooling can authenticate against it.

    key_hash is a SHA-256 hex digest, not Fernet-encrypted — API keys are
    high-entropy random tokens (not human passwords), so a fast deterministic
    hash is the right tool (matches how GitHub/Stripe/AWS handle PATs): it
    lets lookup be an indexed equality query instead of a per-row verify
    loop, and there is nothing to "recover" — a lost key is simply revoked
    and replaced. The raw key is shown to the user exactly once, at creation.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True, foreign_key="user.id")
    key_hash: str = Field(index=True, unique=True)
    label: str = Field(default="")
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    last_used_at: Optional[datetime.datetime] = Field(default=None)
    revoked: bool = Field(default=False)
