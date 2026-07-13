from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional
import uuid
from app.models.price_negotiation import NegotiationType, NegotiationStatus  # import enums

class PriceNegotiationCreate(BaseModel):
    service_id: uuid.UUID
    receiver_id: uuid.UUID
    proposed_price_cents: int
    message: Optional[str] = None
    payment_method: Optional[str] = "platform"

class PriceNegotiationUpdate(BaseModel):
    proposed_price_cents: Optional[int] = None
    message: Optional[str] = None
    status: Optional[NegotiationStatus] = None
    payment_method: Optional[str] = None

from app.schemas.services import ServiceRead
from app.schemas.user import UserRead

class PriceNegotiationRead(BaseModel):
    id: uuid.UUID
    service_id: uuid.UUID
    initiator_id: uuid.UUID
    receiver_id: uuid.UUID
    negotiation_type: NegotiationType
    proposed_price_cents: int
    message: Optional[str]
    status: NegotiationStatus
    payment_method: Optional[str] = "platform"
    created_at: datetime
    updated_at: datetime
    posted_job_id: Optional[uuid.UUID] = None
    services: Optional[ServiceRead] = None
    initiator: Optional[UserRead] = None
    receiver: Optional[UserRead] = None

    model_config = ConfigDict(from_attributes=True)
