from datetime import datetime, timezone

from sqlalchemy import DateTime
from sqlmodel import Column, Field, Relationship, SQLModel, func
from authentication.models import User

    
class Tag2Link(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    link_id: int = Field(foreign_key="link.id")
    tag_id: int = Field(foreign_key="tag.id")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now()),
    )

class Link(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str
    url: str
    created_by_id: int = Field(foreign_key="user.id")
    image: str | None = Field(default=None)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True))
    )
    updated_at: datetime | None = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), onupdate=func.now())
    )
    tags: list["Tag"] = Relationship(link_model=Tag2Link)
    

class Tag(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True))
    )
    updated_at: datetime | None = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), onupdate=func.now())
    )