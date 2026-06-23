import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class Investigation(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    kind: str
    query: str
    created_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.utcnow())
    updated_at: Optional[datetime.datetime] = Field(default=None)
    result_json: str
    confidence: Optional[str] = Field(default="UNVERIFIED")  # CONFIRMED | POSSIBLE | UNVERIFIED
    tags: str = Field(default="")  # comma-separated: key_evidence,follow_up,disputed
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    case_id: Optional[int] = Field(default=None, foreign_key="case.id", index=True)
