import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel
from app.models.notifications import NotificationType


class NotificationCreate(BaseModel):
    user_id: uuid.UUID
    price_negotiation_id: Optional[uuid.UUID] = None
    type: NotificationType = NotificationType.general
    message: str
    metadataInfo: Dict[str, Any] = {}


class NotificationUpdate(BaseModel):
    is_read: Optional[bool] = None
    read_at: Optional[datetime] = None


class NotificationRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    actor_id: Optional[uuid.UUID]
    price_negotiation_id: Optional[uuid.UUID]
    type: NotificationType
    message: str
    metadataInfo: Dict[str, Any]
    is_read: bool
    created_at: datetime
    read_at: Optional[datetime]

    class Config:
        from_attributes = True