from sqlmodel import SQLModel, Field
from typing import Optional
import datetime


class Team(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: str = Field(default="")
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    owner_user_id: Optional[int] = Field(default=None, index=True)


class TeamMember(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    team_id: int = Field(index=True)
    user_id: int = Field(index=True)
    role: str = Field(default="member")  # owner, admin, analyst, member
    joined_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
