# app/schemas/escrow.py
from pydantic import BaseModel, Field
from typing import Optional
import uuid
from enum import Enum
from datetime import datetime

class EscrowStatusStr(str, Enum):
    held = "held"
    released = "released"
    refunded = "refunded"
    disputed = "disputed"


class EscrowCreate(BaseModel):
    payment_negotiation_id: uuid.UUID
    amount_cents: int = Field(..., ge=0)
    reference: Optional[str] = None


class EscrowRead(BaseModel):
    id: uuid.UUID
    payment_negotiation_id: uuid.UUID
    payer_wallet_id: uuid.UUID
    payee_wallet_id: uuid.UUID
    amount_cents: int
    status: EscrowStatusStr

    class Config:
        from_attributes = True


class EscrowActionResponse(BaseModel):
    id: uuid.UUID
    status: EscrowStatusStr
    message: str
    class Config:
        from_attributes = True
