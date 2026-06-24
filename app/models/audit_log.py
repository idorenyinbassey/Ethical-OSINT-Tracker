import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class AuditLog(SQLModel, table=True):
    __tablename__ = "auditlog"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None)
    username: str = Field(default="")
    action: str                          # e.g. login, investigation.run, case.create
    entity_type: str = Field(default="")
    entity_id: Optional[int] = Field(default=None)
    detail: str = Field(default="")      # free-text or JSON snippet
    ip: str = Field(default="")
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
