import enum
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from enum import Enum

from sqlalchemy import UniqueConstraint, ForeignKey
from sqlmodel import SQLModel, Field, Relationship, Column, JSON
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP, ENUM, JSONB


class MessageContentType(str, Enum):
    text = "text"
    image = "image"
    video = "video"
    file = "file"

class MessageStatus(str, Enum):
    sent = "sent"
    delivered = "delivered"
    read = "read"
    failed = "failed"

class Message(SQLModel, table=True):
    __tablename__ = "messages"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, unique=True, nullable=False)
    )
    conversation_id: uuid.UUID = Field(
        sa_column=Column(UUID(as_uuid=True),ForeignKey("conversations.id"), nullable=False, index=True,)
    )
    sender_id: uuid.UUID = Field(
        sa_column=Column(UUID(as_uuid=True),ForeignKey("users.id"), nullable=False, index=True )
    )

    content: str = Field(nullable=False)
    content_type: MessageContentType = Field(nullable=False)
    reply_to_message_id: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(UUID(as_uuid=True), ForeignKey("messages.id"), nullable=True )
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True), nullable=False)
    )
    edited_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(TIMESTAMP(timezone=True), nullable=True)
    )

    status: MessageStatus = Field(nullable=False, default=MessageStatus.sent)

    metadataInfo: Dict[str, Any] = Field(
        sa_column=Column(JSON, nullable=False), default_factory=dict
    )

    conversation: "Conversation" = Relationship(back_populates="messages")
    sender: "Users" = Relationship(back_populates="messages")
    reply_to_message: Optional["Message"] = Relationship(
        back_populates="replies",
        sa_relationship_kwargs={
            "remote_side": "Message.id"
        }
    )
    replies: list["Message"] = Relationship(back_populates="reply_to_message")
    attachments: list["MessageAttachment"] = Relationship(back_populates="message")
    read_receipts: "MessageReadReceipt" = Relationship(back_populates="message")


class MessageAttachment(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False)
    message_id: uuid.UUID = Field(foreign_key="messages.id", nullable=False)
    s3_key: str = Field(nullable=False, index=True)
    mime_type: Optional[str] = Field(default=None)
    size_bytes: Optional[int] = Field(default=None)
    thumbnail_s3_key: Optional[str] = Field(default=None)
    processed: bool = Field(default=False, nullable=False)
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        nullable=False,
        sa_column_kwargs={"server_default": "now()"},
    )
    message: "Message" = Relationship(back_populates="attachments")



class MessageReadReceipt(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("message_id", "user_id"),)
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False)
    message_id: uuid.UUID = Field(foreign_key="messages.id", nullable=False)
    user_id: uuid.UUID = Field(foreign_key="users.id", nullable=False)

    read_at: datetime = Field(
        default_factory=lambda:datetime.now(timezone.utc),
        nullable=False,
        sa_column_kwargs={"server_default": "now()"},
    )
    message: "Message" = Relationship(back_populates="read_receipts")
    user: "Users" = Relationship(back_populates="read_receipts")


class PresenceStatusEnum(str, enum.Enum):
    online = "online"
    offline = "offline"
    away = "away"
    dnd = "dnd"

class Presence(SQLModel, table=True):
    user_id: uuid.UUID = Field(foreign_key="users.id", primary_key=True)

    last_seen: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False,
        sa_column_kwargs={"server_default": "now()"},
    )
    status: PresenceStatusEnum = Field(default=PresenceStatusEnum.offline, nullable=False)
    device_info: Optional[dict] = Field(default=None, sa_column=Column(JSON))

    user: "Users" = Relationship(back_populates="presence")