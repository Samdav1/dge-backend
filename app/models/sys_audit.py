import enum
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import Column, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class AuditLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    actor_type: Optional[str] = Field(default=None, index=True)
    actor_id: Optional[UUID] = Field(default=None, index=True)
    action: str = Field(nullable=False, index=True)
    entity_type: Optional[str] = Field(default=None, index=True)
    entity_id: Optional[UUID] = Field(default=None, index=True)
    metadata_info: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(
        default_factory=lambda :datetime.now(timezone.utc),
        nullable=False,
        index=True,
        sa_column_kwargs={"server_default": "now()"},
    )

class EventStatusEnum(str, enum.Enum):
    pending = "pending"
    published = "published"
    failed = "failed"

class Event(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    event_type: str = Field(nullable=False, index=True)
    source: Optional[str] = Field(default=None)
    entity_id: Optional[UUID] = Field(default=None, index=True)
    payload: dict = Field(sa_column=Column(JSON, nullable=False))
    correlation_id: Optional[UUID] = Field(default=None, index=True)
    causation_id: Optional[int] = Field(default=None, index=True)
    status: EventStatusEnum = Field(
        default=EventStatusEnum.pending, nullable=False, index=True
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        nullable=False,
        sa_column_kwargs={"server_default": "now()"},
    )
    published_at: Optional[datetime] = Field(default=None)