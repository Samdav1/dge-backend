# app/schemas/transactions_repo.py
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime
from uuid import UUID
from app.models.transactions import TxnType, TxnStatus


class TransactionBase(BaseModel):
    wallet_id: UUID
    users_id: UUID
    type: TxnType
    amount_cents: int = Field(..., gt=0, description="Amount in cents (must be > 0)")


class TransactionCreate(TransactionBase):
    reference: Optional[str] = None
    status: TxnStatus



class TransactionRead(TransactionBase):
    id: UUID
    status: TxnStatus
    reference: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
class TransactionUpdate(BaseModel):
    status: Optional[TxnStatus] = None
    reference: Optional[str] = None
