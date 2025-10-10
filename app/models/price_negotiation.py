import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlmodel import SQLModel, Field, Column, ForeignKey, Relationship
from sqlalchemy import Enum, BigInteger, Text, UUID, DateTime
import enum

class NegotiationType(str, enum.Enum):
    incoming = "incoming"
    outgoing = "outgoing"


class NegotiationStatus(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"
    rejected = "rejected"
    countered = "countered"


class PriceNegotiation(SQLModel, table=True):
    __tablename__ = "price_negotiations"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True,
        nullable=False
    )

    service_id: uuid.UUID = Field(
        sa_column=Column(UUID(as_uuid=True),ForeignKey("services.id"), nullable=False, index=True)
    )

    initiator_id: uuid.UUID = Field(
        sa_column=Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    )
    receiver_id: uuid.UUID = Field(
        sa_column=Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    )

    negotiation_type: NegotiationType = Field(
        sa_column=Column(Enum(NegotiationType, name="negotiation_type_enum"), nullable=False)
    )
    proposed_price_cents: int = Field(
        sa_column=Column(BigInteger, nullable=False)
    )
    message: str | None = Field(
        sa_column=Column(Text, nullable=True)
    )
    status: NegotiationStatus = Field(
        sa_column=Column(Enum(NegotiationStatus, name="negotiation_status_enum"), nullable=False, default=NegotiationStatus.pending)
    )

    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False),
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False),
        default_factory=lambda: datetime.now(timezone.utc)
    )

    services: "Service" = Relationship(back_populates="negotiations")
    initiator: "Users" = Relationship(back_populates="negotiations_outgoing", sa_relationship_kwargs={"foreign_keys": "[PriceNegotiation.initiator_id]"})
    receiver: "Users" = Relationship(back_populates="negotiations_incoming", sa_relationship_kwargs={"foreign_keys": "[PriceNegotiation.receiver_id]"})
    escrow: 'Escrow' = Relationship(back_populates="price_negotiation")
    notifications: list['Notification'] = Relationship(back_populates="price_negotiation")
