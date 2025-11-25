from sqlmodel import SQLModel, Field
from typing import Optional
import datetime


class APIConfig(SQLModel, table=True):
    """Store API configurations for external OSINT services"""
    id: Optional[int] = Field(default=None, primary_key=True)
    service_name: str = Field(index=True)  # whoisxml, hibp, ipinfo, etc.
    api_key: str  # Encrypted in production
    base_url: str
    is_enabled: bool = Field(default=True)
    rate_limit: int = Field(default=100)  # requests per hour
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
    notes: str = Field(default="")
