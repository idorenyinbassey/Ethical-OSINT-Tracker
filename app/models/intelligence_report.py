from sqlmodel import SQLModel, Field
from typing import Optional
import datetime


class IntelligenceReport(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    summary: str = Field(default="")
    indicators: str = Field(default="")  # JSON string of IoCs
    related_case_id: Optional[int] = Field(default=None, index=True)
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    author_user_id: Optional[int] = Field(default=None, index=True)
