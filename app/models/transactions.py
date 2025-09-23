import uuid

from sqlmodel import SQLModel, Field, Column, ForeignKey, Relationship
from sqlalchemy import Enum, BigInteger
import enum

class TxnType(str, enum.Enum):
    deposit = "deposit"
    withdrawal = "withdrawal"
    transfer = "transfer"
    payment = "payment"
    refund = "refund"
    escrow_release = "escrow_release"


class TxnStatus(str, enum.Enum):
    pending = "pending"
    completed = "completed"
    failed = "failed"
    reversed = "reversed"


class Transaction(SQLModel, table=True):
    __tablename__ = "transactions"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True,
        nullable=False
    )

    wallet_id: uuid.UUID = Field(
        sa_column=Column("wallet_id", ForeignKey("wallets.id"), nullable=False)
    )

    type: TxnType = Field(
        sa_column=Column(Enum(TxnType, name="txn_type_enum"), nullable=False, index=True)
    )

    amount_cents: int = Field(
        sa_column=Column(BigInteger, nullable=False)
    )

    status: TxnStatus = Field(
        sa_column=Column(Enum(TxnStatus, name="txn_status_enum"), nullable=False, default=TxnStatus.pending, index=True)
    )

    reference: str = Field(
        default=None,
        nullable=True,
        index=True
    )
    user: 'User' = Relationship(back_populates="transactions")