import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field, Column, ForeignKey, Relationship
from sqlalchemy import Enum, BigInteger, DateTime, String, Boolean, Text
import enum


class DepositStatus(str, enum.Enum):
    pending = "pending"              # Monnify payment initiated, awaiting webhook
    confirmed = "confirmed"          # Monnify confirmed payment received
    screened_pending = "screened_pending"  # Deposit held for admin approval
    approved = "approved"            # Admin approved (wallet credited)
    failed = "failed"
    expired = "expired"


class WithdrawalStatus(str, enum.Enum):
    pending = "pending"              # Awaiting admin approval (or auto-processing)
    approved = "approved"            # Admin approved, queued for transfer
    processing = "processing"        # Monnify transfer initiated
    completed = "completed"          # Funds sent
    rejected = "rejected"            # Admin rejected
    failed = "failed"                # Monnify transfer failed


class DepositRequest(SQLModel, table=True):
    __tablename__ = "deposit_requests"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True,
        nullable=False
    )
    user_id: uuid.UUID = Field(
        sa_column=Column("user_id", ForeignKey("users.id"), nullable=False, index=True)
    )
    wallet_id: uuid.UUID = Field(
        sa_column=Column("wallet_id", ForeignKey("wallets.id"), nullable=False)
    )
    amount_cents: int = Field(
        sa_column=Column(BigInteger, nullable=False)
    )
    currency: str = Field(default="NGN", nullable=False)
    monnify_reference: Optional[str] = Field(
        default=None,
        sa_column=Column(String, nullable=True, index=True)
    )
    monnify_transaction_ref: Optional[str] = Field(
        default=None,
        sa_column=Column(String, nullable=True, index=True)
    )
    payment_link: Optional[str] = Field(
        default=None,
        sa_column=Column(String, nullable=True)
    )
    # Virtual account details (for DVA flow)
    virtual_account_number: Optional[str] = Field(
        default=None,
        sa_column=Column(String, nullable=True)
    )
    virtual_bank_name: Optional[str] = Field(
        default=None,
        sa_column=Column(String, nullable=True)
    )
    status: DepositStatus = Field(
        sa_column=Column(Enum(DepositStatus, name="deposit_status_enum"), nullable=False, default=DepositStatus.pending, index=True)
    )
    approved_by_admin_id: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column("approved_by_admin_id", ForeignKey("superadmin.id"), nullable=True)
    )
    metadata_json: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True)  # Stores raw Monnify webhook payload
    )
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False),
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False),
        default_factory=lambda: datetime.now(timezone.utc)
    )


class WithdrawalRequest(SQLModel, table=True):
    __tablename__ = "withdrawal_requests"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True,
        nullable=False
    )
    user_id: uuid.UUID = Field(
        sa_column=Column("user_id", ForeignKey("users.id"), nullable=False, index=True)
    )
    wallet_id: uuid.UUID = Field(
        sa_column=Column("wallet_id", ForeignKey("wallets.id"), nullable=False)
    )
    bank_account_id: uuid.UUID = Field(
        sa_column=Column("bank_account_id", ForeignKey("user_bank_accounts.id"), nullable=False)
    )
    amount_cents: int = Field(
        sa_column=Column(BigInteger, nullable=False)
    )
    currency: str = Field(default="NGN", nullable=False)
    monnify_reference: Optional[str] = Field(
        default=None,
        sa_column=Column(String, nullable=True, index=True)
    )
    status: WithdrawalStatus = Field(
        sa_column=Column(Enum(WithdrawalStatus, name="withdrawal_status_enum"), nullable=False, default=WithdrawalStatus.pending, index=True)
    )
    rejection_reason: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True)
    )
    approved_by_admin_id: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column("approved_by_admin_id", ForeignKey("superadmin.id"), nullable=True)
    )
    reviewed_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False),
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False),
        default_factory=lambda: datetime.now(timezone.utc)
    )


class UserBankAccount(SQLModel, table=True):
    __tablename__ = "user_bank_accounts"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True,
        nullable=False
    )
    user_id: uuid.UUID = Field(
        sa_column=Column("user_id", ForeignKey("users.id"), nullable=False, index=True)
    )
    account_number: str = Field(
        sa_column=Column(String(20), nullable=False)
    )
    account_name: str = Field(
        sa_column=Column(String(200), nullable=False)
    )
    bank_code: str = Field(
        sa_column=Column(String(10), nullable=False)
    )
    bank_name: str = Field(
        sa_column=Column(String(100), nullable=False)
    )
    is_default: bool = Field(
        sa_column=Column(Boolean, nullable=False, default=False)
    )
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False),
        default_factory=lambda: datetime.now(timezone.utc)
    )
