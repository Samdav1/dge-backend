import uuid
from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel
from enum import Enum


class ConversationType(str, Enum):
    private = "private"
    group = "group"
    support = "support"



class ConversationParticipantBase(BaseModel):
    conversation_id: uuid.UUID
    user_id: uuid.UUID
    role: str = "member"


class ConversationParticipantCreate(ConversationParticipantBase):
    pass


class ConversationParticipantRead(ConversationParticipantBase):
    id: uuid.UUID
    joined_at: datetime
    left_at: Optional[datetime] = None

    class Config:
        orm_mode = True



class ConversationBase(BaseModel):
    title: Optional[str] = None
    type: ConversationType
    metadataInfo: Dict = {}


class ConversationCreate(ConversationBase):
    created_by: uuid.UUID


class ConversationUpdate(BaseModel):
    title: Optional[str] = None
    metadataInfo: Optional[Dict] = None


class ConversationRead(ConversationBase):
    id: uuid.UUID
    created_by: uuid.UUID
    created_at: datetime
    last_message_id: Optional[uuid.UUID] = None

    # ✅ nested relationships
    # participants: List[ConversationParticipantRead] = []

    class Config:
        from_attributes = True
