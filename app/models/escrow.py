import uuid
from sqlmodel import SQLModel, Field, Column, ForeignKey, Relationship
from sqlalchemy import Enum, BigInteger
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
        sa_column=Column("payer_wallet_id", ForeignKey("wallets.id"), nullable=False)
    )
    payee_wallet_id: uuid.UUID = Field(
        sa_column=Column("payee_wallet_id", ForeignKey("wallets.id"), nullable=False)
    )
    amount_cents: int = Field(
        sa_column=Column(BigInteger, nullable=False)
    )
    status: EscrowStatus = Field(
        sa_column=Column(Enum(EscrowStatus, name="escrow_status_enum"), nullable=False, default=EscrowStatus.held)
    )
    payer_wallet: "Wallet" = Relationship(
        back_populates="escrows_as_payer",
        sa_relationship_kwargs={"foreign_keys": "[Escrow.payer_wallet_id]"}
    )
    payee_wallet: "Wallet" = Relationship(
        back_populates="escrows_as_payee",
        sa_relationship_kwargs={"foreign_keys": "[Escrow.payee_wallet_id]"}
    )
