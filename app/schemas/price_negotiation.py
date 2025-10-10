from pydantic import BaseModel
from datetime import datetime
from typing import Optional
import uuid
from app.models.price_negotiation import NegotiationType, NegotiationStatus  # import enums

class PriceNegotiationCreate(BaseModel):
    service_id: uuid.UUID
    receiver_id: uuid.UUID
    proposed_price_cents: int
    message: Optional[str] = None

class PriceNegotiationUpdate(BaseModel):
    proposed_price_cents: Optional[int] = None
    message: Optional[str] = None
    status: Optional[NegotiationStatus] = None

class PriceNegotiationRead(BaseModel):
    id: uuid.UUID
    service_id: uuid.UUID
    initiator_id: uuid.UUID
    receiver_id: uuid.UUID
    negotiation_type: NegotiationType
    proposed_price_cents: int
    message: Optional[str]
    status: NegotiationStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True