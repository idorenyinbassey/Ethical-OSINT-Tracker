from datetime import datetime
from sqlmodel import SQLModel, Field

class AuditLog(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    event: str = Field(max_length=255, description="Short event description")
    detail: str | None = Field(default=None, description="Optional extended detail JSON or text")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp of event creation")
