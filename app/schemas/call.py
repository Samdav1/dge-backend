from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel
from enum import Enum


class CallTypeEnum(str, Enum):
    audio = "audio"
    video = "video"


class CallStatusEnum(str, Enum):
    initiated = "initiated"
    connected = "connected"
    ended = "ended"
    missed = "missed"


# ---------- CREATE ----------
class CallSessionCreate(BaseModel):
    conversation_id: Optional[UUID] = None
    call_type: CallTypeEnum


# ---------- READ ----------
class CallSessionRead(BaseModel):
    id: UUID
    conversation_id: Optional[UUID]
    initiator_id: Optional[UUID]
    call_type: CallTypeEnum
    status: CallStatusEnum
    started_at: Optional[datetime]
    ended_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- PARTICIPANT ----------
class CallParticipantCreate(BaseModel):
    call_session_id: UUID
    muted: bool = False
    role: Optional[str] = "participant"


class CallRecordingCreate(BaseModel):
    call_session_id: UUID
    s3_key: str
    size_bytes: Optional[int] = None
    duration_seconds: Optional[int] = None