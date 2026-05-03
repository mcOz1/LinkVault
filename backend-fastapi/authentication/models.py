
from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    username: str
    email: str | None = None
    full_name: str | None = None
    active: bool | None = Field(default=True, nullable=False)
    hashed_password: str
    is_superuser: bool | None = None
    