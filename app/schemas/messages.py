# app/schemas/message.py
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from enum import Enum

class MessageContentType(str, Enum):
    text = "text"
    image = "image"
    video = "video"
    file = "file"


class MessageStatus(str, Enum):
    sent = "sent"
    delivered = "delivered"
    read = "read"
    failed = "failed"


class PresenceStatusEnum(str, Enum):
    online = "online"
    offline = "offline"
    away = "away"
    dnd = "dnd"

class MessageAttachmentBase(BaseModel):
    s3_key: str
    mime_type: Optional[str] = None
    size_bytes: Optional[int] = None
    thumbnail_s3_key: Optional[str] = None
    processed: bool = False


class MessageAttachmentCreate(MessageAttachmentBase):
    pass


class MessageAttachmentRead(MessageAttachmentBase):
    id: uuid.UUID
    message_id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True

class MessageReadReceiptBase(BaseModel):
    pass


class MessageReadReceiptCreate(MessageReadReceiptBase):
    message_id: uuid.UUID
    user_id: uuid.UUID


class MessageReadReceiptRead(MessageReadReceiptBase):
    id: uuid.UUID
    message_id: uuid.UUID
    user_id: uuid.UUID
    read_at: datetime

    class Config:
        from_attributes = True

class MessageBase(BaseModel):
    content: str
    content_type: MessageContentType
    metadataInfo: Dict[str, Any] = {}


class MessageCreate(MessageBase):
    conversation_id: uuid.UUID
    sender_id: uuid.UUID
    reply_to_message_id: Optional[uuid.UUID] = None


class MessageUpdate(BaseModel):
    content: Optional[str] = None
    status: Optional[MessageStatus] = None
    edited_at: Optional[datetime] = None


class MessageRead(MessageBase):
    id: uuid.UUID
    conversation_id: uuid.UUID
    sender_id: uuid.UUID
    reply_to_message_id: Optional[uuid.UUID]
    created_at: datetime
    edited_at: Optional[datetime]
    status: MessageStatus

    # nested relationships
    # attachments: List[MessageAttachmentRead] = []
    # replies: List["MessageRead"] = []
    # read_receipts: List[MessageReadReceiptRead] = []

    class Config:
        from_attributes = True


MessageRead.model_rebuild()  # for self-referencing replies

class PresenceBase(BaseModel):
    status: PresenceStatusEnum
    device_info: Optional[Dict] = None


class PresenceCreate(PresenceBase):
    pass


class PresenceUpdate(BaseModel):
    status: Optional[PresenceStatusEnum] = None
    device_info: Optional[Dict] = None
    last_seen: Optional[datetime] = None


class PresenceRead(BaseModel):
    device_info: Optional[Dict] = None
    status: PresenceStatusEnum
    user_id: uuid.UUID
    last_seen: datetime

    class Config:
        from_attributes = True

