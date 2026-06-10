import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from app.models.payment_request import DepositStatus, WithdrawalStatus


# ─── Bank Account Schemas ────────────────────────────────────────────────────

class BankAccountVerifyRequest(BaseModel):
    account_number: str
    bank_code: str


class BankAccountVerifyResponse(BaseModel):
    account_number: str
    account_name: str
    bank_code: str
    bank_name: str


class BankAccountCreate(BaseModel):
    account_number: str
    account_name: str
    bank_code: str
    bank_name: str
    is_default: bool = False


class BankAccountRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    account_number: str
    account_name: str
    bank_code: str
    bank_name: str
    is_default: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Deposit Schemas ─────────────────────────────────────────────────────────

class DepositInitiateRequest(BaseModel):
    amount: float  # In Naira (not cents)


class DepositInitiateResponse(BaseModel):
    deposit_id: uuid.UUID
    amount_naira: float
    monnify_reference: str
    payment_link: Optional[str] = None
    virtual_account_number: Optional[str] = None
    virtual_bank_name: Optional[str] = None
    status: DepositStatus
    message: str


class DepositRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    amount_cents: int
    currency: str
    monnify_reference: Optional[str]
    status: DepositStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ─── Withdrawal Schemas ──────────────────────────────────────────────────────

class WithdrawalRequestCreate(BaseModel):
    amount: float  # In Naira
    bank_account_id: uuid.UUID


class WithdrawalRequestRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    amount_cents: int
    currency: str
    status: WithdrawalStatus
    rejection_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WithdrawalRequestAdminRead(BaseModel):
    """Extended read schema for admin views — includes bank account info."""
    id: uuid.UUID
    user_id: uuid.UUID
    amount_cents: int
    currency: str
    status: WithdrawalStatus
    rejection_reason: Optional[str] = None
    bank_account_number: Optional[str] = None
    bank_account_name: Optional[str] = None
    bank_name: Optional[str] = None
    user_email: Optional[str] = None
    user_username: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WithdrawalRejectRequest(BaseModel):
    reason: str


# ─── Admin Payment Settings Schemas ──────────────────────────────────────────

class AdminPaymentSettingsRead(BaseModel):
    id: int
    auto_approve_withdrawals: bool
    screen_deposits: bool
    updated_at: datetime

    class Config:
        from_attributes = True


class AdminPaymentSettingsUpdate(BaseModel):
    auto_approve_withdrawals: Optional[bool] = None
    screen_deposits: Optional[bool] = None
