import datetime
from sqlmodel import SQLModel, Field


class Investigation(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    kind: str
    query: str
    created_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.utcnow())
    result_json: str
    user_id: int | None = Field(default=None, foreign_key="user.id")
