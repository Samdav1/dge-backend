import uuid
from typing import Optional
from sqlmodel import SQLModel, Field, Column, ForeignKey, Relationship
from sqlalchemy import Enum, BigInteger
import enum


class WalletType(str, enum.Enum):
    deposit = "deposit"
    earnings = "earnings"

class Wallet(SQLModel, table=True):
    __tablename__ = "wallets"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True,
        nullable=False
    )
    user_id: uuid.UUID = Field(
        sa_column=Column("user_id", ForeignKey("users.id"), nullable=False)
    )
    wallet_type: WalletType = Field(
        sa_column=Column(Enum(WalletType, name="wallet_type_enum"), nullable=False)
    )
    balance_cents: float = Field(
        sa_column=Column(BigInteger, nullable=False, default=0)
    )
    currency: str = Field(default="USD", nullable=False)

    user : 'Users' = Relationship(back_populates="wallet")

    escrows_as_payer: list["Escrow"] = Relationship(
        back_populates="payer_wallet",
        sa_relationship_kwargs={"foreign_keys": "[Escrow.payer_wallet_id]"}
    )
    escrows_as_payee: list["Escrow"] = Relationship(
        back_populates="payee_wallet",
        sa_relationship_kwargs={"foreign_keys": "[Escrow.payee_wallet_id]"}
    )