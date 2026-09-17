from sqlmodel import SQLModel, Field
from typing import Optional
import datetime


class Case(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    description: str = Field(default="")
    status: str = Field(default="open")  # open | in_progress | closed
    priority: str = Field(default="medium")  # low | medium | high | critical
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    owner_user_id: Optional[int] = Field(default=None, index=True)
    # Optional team the case is shared with (nullable — unshared/personal by
    # default). Set via POST /cases/<id>/share. See app/utils/authz.py for
    # the read/comment/export/edit/delete matrix per team role.
    team_id: Optional[int] = Field(default=None, index=True)
