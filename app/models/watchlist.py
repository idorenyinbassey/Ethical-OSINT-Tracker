import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class WatchlistTarget(SQLModel, table=True):
    __tablename__ = "watchlist"
    id: Optional[int] = Field(default=None, primary_key=True)
    query: str
    kind: str  # ip | domain | email | social | crypto | phone
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    case_id: Optional[int] = Field(default=None, foreign_key="case.id", index=True)
    notes: str = Field(default="")
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    last_checked: Optional[datetime.datetime] = Field(default=None)
    last_result_hash: str = Field(default="")
    has_alert: bool = Field(default=False)
    alert_message: str = Field(default="")
