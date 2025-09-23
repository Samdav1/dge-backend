import enum
from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel


class CallTypeEnum(str, enum.Enum):
    audio = "audio"
    video = "video"


class CallStatusEnum(str, enum.Enum):
    initiated = "initiated"
    connected = "connected"
    ended = "ended"
    missed = "missed"


class CallSession(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True, nullable=False)
    conversation_id: Optional[UUID] = Field(default=None, foreign_key="conversations.id")
    initiator_id: Optional[UUID] = Field(default=None, foreign_key="users.id")
    call_type: CallTypeEnum = Field(nullable=False)
    status: CallStatusEnum = Field(default=CallStatusEnum.initiated, nullable=False)

    started_at: Optional[datetime] = Field(default=None)
    ended_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        nullable=False,
        sa_column_kwargs={"server_default": "now()"},
    )
    signaling_metadata: Optional[dict] = Field(default=None, sa_column=Column(JSONB))

    conversation: Optional["Conversation"] = Relationship(back_populates="call_sessions")
    initiator: Optional["Users"] = Relationship(back_populates="initiated_calls")
    participants: List["CallParticipant"] = Relationship(back_populates="call_session")