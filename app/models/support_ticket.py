import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Any

from sqlalchemy import Column, JSON
from sqlmodel import SQLModel, Field, Relationship


class SupportTicketStatus(str, Enum):
    open = "open"
    in_progress = "in_progress"
    resolved = "resolved"
    closed = "closed"


class SupportTicketPriority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    urgent = "urgent"


class SupportTicket(SQLModel, table=True):
    __tablename__ = "support_tickets"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)

    user_id: uuid.UUID = Field(foreign_key="users.id", nullable=False, index=True)
    assigned_to: Optional[uuid.UUID] = Field(
        default=None, foreign_key="teamusers.id", index=True
    )

    subject: str = Field(nullable=False, description="Short subject of the ticket")
    description: str = Field(nullable=False, description="Detailed description")

    status: SupportTicketStatus = Field(
        default=SupportTicketStatus.open, nullable=False
    )
    priority: SupportTicketPriority = Field(
        default=SupportTicketPriority.medium, nullable=False
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), nullable=False
    )

    user: "Users" = Relationship(back_populates="support_tickets")
    assigned_team_user: Optional["TeamUsers"] = Relationship(back_populates="assigned_tickets")
    replies: list["SupportTicketReply"] = Relationship(back_populates="ticket")


class SupportTicketReply(SQLModel, table=True):
    __tablename__ = "support_ticket_replies"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)

    # Foreign keys
    ticket_id: uuid.UUID = Field(foreign_key="support_tickets.id", nullable=False, index=True)
    author_user_id: Optional[uuid.UUID] = Field(
        default=None, foreign_key="users.id", index=True
    )
    author_team_user_id: Optional[uuid.UUID] = Field(
        default=None, foreign_key="teamusers.id", index=True
    )

    message: str = Field(nullable=False, description="The content of the reply")

    attachments: Dict[str, Any] = Field(
        sa_column=Column(JSON, nullable=False), default_factory=dict
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), nullable=False
    )

    ticket: "SupportTicket" = Relationship(back_populates="replies")
    author_user: Optional["Users"] = Relationship(back_populates="ticket_replies")
    author_team_user: Optional["TeamUsers"] = Relationship(back_populates="ticket_replies")

