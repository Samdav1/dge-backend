import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from enum import Enum

from sqlalchemy import UUID, TIMESTAMP, String, ForeignKey
from sqlmodel import SQLModel, Field, Relationship, Column, JSON


class ConversationType(str, Enum):
    private = "private"
    group = "group"
    support = "support"


class ConversationParticipant(SQLModel, table=True):
    __tablename__ = "conversation_participants"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, unique=True, nullable=False),
    )

    conversation_id: uuid.UUID = Field(
        sa_column=Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False, index=True, )
    )
    user_id: uuid.UUID = Field(
        sa_column=Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True, )
    )

    joined_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(TIMESTAMP(timezone=True), nullable=False),
    )
    left_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(TIMESTAMP(timezone=True), nullable=True),
    )

    role: str = Field(
        default="member",
        sa_column=Column(String, nullable=False),
    )

    # Relationships
    conversation: "Conversation" = Relationship(back_populates="participants")
    user: "Users" = Relationship(back_populates="conversations")


class Conversation(SQLModel, table=True):
    __tablename__ = "conversations"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, unique=True, nullable=False),
    )

    title: Optional[str] = Field(default=None, nullable=True)
    type: str = Field(sa_column=Column(String, nullable=False))
    created_by: uuid.UUID = Field(sa_column=Column(UUID(as_uuid=True), nullable=False))
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True), nullable=False),
    )

    last_message_id: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(UUID(as_uuid=True), nullable=True),
    )

    metadataInfo: dict = Field(default_factory=dict, sa_column=Column(JSON))

    # Relationships
    participants: list["ConversationParticipant"] = Relationship(back_populates="conversation")
    messages: list["Message"] = Relationship(back_populates="conversation")




