import datetime
from sqlmodel import SQLModel, Field
from flask_login import UserMixin


class User(UserMixin, SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    password_hash: str
    created_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.utcnow())
    is_active: bool = Field(default=True, sa_column_kwargs={"name": "is_active"})

    def get_id(self) -> str:
        return str(self.id)

    @property
    def active(self) -> bool:
        return self.is_active
