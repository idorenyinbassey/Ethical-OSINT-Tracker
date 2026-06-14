import datetime
from typing import Optional
from sqlmodel import SQLModel, Field

class CaseComment(SQLModel, table=True):
    __tablename__ = "casecomment"
    id: Optional[int] = Field(default=None, primary_key=True)
    case_id: int = Field(foreign_key="case.id", index=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    username: str = Field(default="")
    body: str
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
