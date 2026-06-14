from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict
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
    channel_name: str


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
    channel_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
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


# ---------- AGORA TOKEN ----------
class AgoraTokenRequest(BaseModel):
    channel_name: str = Field(..., description="Agora channel name the client wants to join")
    uid: int = Field(default=0, description="Numeric user ID; 0 lets Agora assign one automatically")
    role: int = Field(default=1, description="1=Publisher (host), 2=Subscriber (audience-only)")
    expire_seconds: int = Field(default=3600, ge=60, le=86400, description="Token TTL in seconds (60–86400)")


class AgoraTokenResponse(BaseModel):
    token: str
    channel_name: str
    uid: int
    app_id: str
    expires_in: int
