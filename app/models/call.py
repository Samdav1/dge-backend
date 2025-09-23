import enum
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, UniqueConstraint, JSON
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
    __tablename__ = "call_session"
    id: UUID = Field(default_factory=uuid4, primary_key=True, nullable=False)
    conversation_id: Optional[UUID] = Field(default=None, foreign_key="conversations.id")
    initiator_id: Optional[UUID] = Field(default=None, foreign_key="users.id")
    call_type: CallTypeEnum = Field(nullable=False)
    status: CallStatusEnum = Field(default=CallStatusEnum.initiated, nullable=False)

    started_at: Optional[datetime] = Field(default=None)
    ended_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(
        default_factory=lambda :datetime.now(timezone.utc),
        nullable=False,
        sa_column_kwargs={"server_default": "now()"},
    )
    signaling_metadata: Optional[dict] = Field(default=None, sa_column=Column(JSON))

    conversation: Optional["Conversation"] = Relationship(back_populates="call_sessions")
    initiator: Optional["Users"] = Relationship(back_populates="initiated_calls")
    participants: List["CallParticipant"] = Relationship(back_populates="call_session")
    recordings: List["CallRecording"] = Relationship(back_populates="call_session")


class CallParticipant(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("call_session_id", "user_id"),)
    id: UUID = Field(default_factory=uuid4, primary_key=True, nullable=False, index=True)
    call_session_id: UUID = Field(foreign_key="call_session.id", nullable=False)
    user_id: UUID = Field(foreign_key="users.id", nullable=False)
    muted: bool = Field(default=False, nullable=False)
    role: Optional[str] = Field(default="participant")
    joined_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    left_at: Optional[datetime] = Field(default=None)
    call_session: "CallSession" = Relationship(back_populates="participants")
    users: "Users" = Relationship(back_populates="call_participations")


class CallRecording(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True, nullable=False, index=True)
    call_session_id: UUID = Field(foreign_key="call_session.id", nullable=False)
    s3_key: str = Field(nullable=False, index=True)
    size_bytes: Optional[int] = Field(default=None)
    duration_seconds: Optional[int] = Field(default=None)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False,
        sa_column_kwargs={"server_default": "now()"},
    )

    call_session: "CallSession" = Relationship(back_populates="recordings")



