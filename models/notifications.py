from typing import Optional

from sqlalchemy import Column, JSON, DateTime
from sqlalchemy.testing.pickleable import User
from sqlmodel import SQLModel, Field, TIMESTAMP, ForeignKey, Relationship
from datetime import datetime, timezone
import uuid
import enum


class NotificationType(str, enum.Enum):
    general = "general"
    offer_rejected = "offer_rejected"
    offer_accepted = "offer_accepted"
    escrow_released = "escrow_released"
    escrow_disputed = "escrow_disputed"


class Notification(SQLModel, table=True):
    __tablename__ = "notifications"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False)
    user_id: uuid.UUID = Field(
        foreign_key="users.id",  # 👈 use lowercase "foreign_key" here in SQLModel
        nullable=False
    )

    # FK to users (actor who triggered event)
    actor_id: Optional[uuid.UUID] = Field(
        foreign_key="users.id",
        nullable=True
    )
# who triggered it
    price_negotiation_id: Optional[uuid.UUID] = Field(
        foreign_key="price_negotiations.id", nullable=True
    )
    type: NotificationType = Field(default=NotificationType.general, nullable=False)
    message: str = Field(nullable=False)
    metadataInfo: dict = Field(default_factory=dict, sa_column=Column(JSON))
    is_read: bool = Field(default=False, nullable=False)
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False),
        default_factory=lambda:datetime.now(timezone.utc),
    )
    read_at: Optional[datetime] = Field(
        sa_column=Column(DateTime(timezone=True)),
    )

    user: "Users" = Relationship(
        back_populates="notifications",
        sa_relationship_kwargs={"foreign_keys": "[Notification.user_id]"}
    )

    actor: Optional["Users"] = Relationship(
        back_populates="notifications_sent",
        sa_relationship_kwargs={"foreign_keys": "[Notification.actor_id]"}
    )
    price_negotiation: Optional['PriceNegotiation'] = Relationship(back_populates="notifications")


class AdminNotification(SQLModel, table=True):
    __tablename__ = "admin_notifications"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False)
    title: str = Field(nullable=False)
    message: str = Field(nullable=False)
    recipients: str = Field(nullable=False)
    type: str = Field(nullable=False)
    status: str = Field(default="DELIVERED", nullable=False)
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False),
        default_factory=lambda: datetime.now(timezone.utc),
    )