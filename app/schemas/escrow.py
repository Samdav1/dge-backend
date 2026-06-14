# app/schemas/escrow.py
from pydantic import BaseModel, Field, ConfigDict
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


class EscrowActionPayload(BaseModel):
    rating: Optional[int] = Field(None, ge=1, le=5)
    review_comment: Optional[str] = None
    direct_message: Optional[str] = None


from app.schemas.price_negotiation import PriceNegotiationRead
from app.schemas.work_submission import WorkSubmissionRead
from app.schemas.wallet import WalletRead
from typing import List

class EscrowRead(BaseModel):
    id: uuid.UUID
    payment_negotiation_id: uuid.UUID
    payer_wallet_id: uuid.UUID
    payee_wallet_id: uuid.UUID
    amount_cents: int
    status: EscrowStatusStr
    created_at: datetime
    price_negotiation: Optional[PriceNegotiationRead] = None
    submissions: List[WorkSubmissionRead] = []
    payer_wallet: Optional[WalletRead] = None
    payee_wallet: Optional[WalletRead] = None

    model_config = ConfigDict(from_attributes=True)
class EscrowActionResponse(BaseModel):
    id: uuid.UUID
    status: EscrowStatusStr
    message: str
    model_config = ConfigDict(from_attributes=True)
