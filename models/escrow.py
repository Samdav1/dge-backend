import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlmodel import SQLModel, Field, Column, ForeignKey, Relationship
from sqlalchemy import Enum, BigInteger, DateTime, Text
import enum


class EscrowStatus(str, enum.Enum):
    held = "held"
    released = "released"
    refunded = "refunded"
    disputed = "disputed"


class Escrow(SQLModel, table=True):
    __tablename__ = "escrow"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True,
        nullable=False
    )
    payer_wallet_id: uuid.UUID = Field(
        sa_column=Column(ForeignKey("wallets.id"),  nullable=False)
    )
    payee_wallet_id: uuid.UUID = Field(
        sa_column=Column(ForeignKey("wallets.id"), nullable=False)
    )
    payment_negotiation_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("price_negotiations.id"),
            nullable=False
        )
    )

    amount_cents: int = Field(
        sa_column=Column(BigInteger, nullable=False)
    )
    status: EscrowStatus = Field(
        sa_column=Column(Enum(EscrowStatus, name="escrow_status_enum"), nullable=False, default=EscrowStatus.held)
    )
    payment_method: Optional[str] = Field(
        default="platform",
        sa_column=Column(Text, nullable=True)
    )
    payer_wallet: "Wallet" = Relationship(
        back_populates="escrows_as_payer",
        sa_relationship_kwargs={"foreign_keys": "[Escrow.payer_wallet_id]"}
    )
    payee_wallet: "Wallet" = Relationship(
        back_populates="escrows_as_payee",
        sa_relationship_kwargs={"foreign_keys": "[Escrow.payee_wallet_id]"}
    )
    price_negotiation: 'PriceNegotiation' = Relationship(back_populates="escrow")
    submissions: List["WorkSubmission"] = Relationship(back_populates="escrow")

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True),
                         nullable=False))

    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    )