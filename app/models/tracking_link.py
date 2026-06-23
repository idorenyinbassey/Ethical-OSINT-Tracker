import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class TrackingLink(SQLModel, table=True):
    __tablename__ = "trackinglink"
    id: Optional[int] = Field(default=None, primary_key=True)
    token: str = Field(index=True)
    label: str
    case_id: Optional[int] = Field(default=None, foreign_key="case.id", index=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    decoy_mode: str = Field(default="404")   # 404 | blank | redirect
    redirect_url: str = Field(default="")
    notes: str = Field(default="")
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
