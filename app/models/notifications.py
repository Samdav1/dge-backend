from typing import Optional

from sqlalchemy import Column, JSON
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
    user_id: uuid.UUID = Field(ForeignKey("users.id"), nullable=False)  # recipient
    actor_id: Optional[uuid.UUID] = Field(ForeignKey("users.id"), nullable=True)  # who triggered it
    price_negotiation_id: Optional[uuid.UUID] = Field(
        ForeignKey("price_negotiations.id"), nullable=True
    )
    type: NotificationType = Field(default=NotificationType.general, nullable=False)
    message: str = Field(nullable=False)
    metadataInfo: dict = Field(default_factory=dict, sa_column=Column(JSON))
    is_read: bool = Field(default=False, nullable=False)
    created_at: datetime = Field(default_factory=lambda:datetime.now(timezone.utc), nullable=False)
    read_at: Optional[datetime] = Field(default=None)

    user: 'Users' = Relationship(back_populates="notifications")
    price_negotiation: Optional['PriceNegotiations'] = Relationship(back_populates="notifications")


