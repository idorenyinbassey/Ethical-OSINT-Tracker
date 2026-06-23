import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class CaseNote(SQLModel, table=True):
    __tablename__ = "casenote"
    id: Optional[int] = Field(default=None, primary_key=True)
    case_id: int = Field(index=True, foreign_key="case.id")
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    username: str = Field(default="")
    kind: str = Field(default="observation")  # observation | lead | key_evidence | follow_up
    body: str
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
