# app/services/call_service.py

from datetime import datetime, timezone
from uuid import uuid4
from app.models.call import CallSession, CallParticipant, CallRecording, CallStatusEnum
from app.repositories.call_repo import CallRepository
from app.schemas.call import CallSessionCreate, CallParticipantCreate, CallRecordingCreate


class CallService:
    def __init__(self, repo: CallRepository):
        self.repo = repo

    async def create_call(self, payload: CallSessionCreate, initiator_id: str):
        new_call = CallSession(
            id=uuid4(),
            conversation_id=payload.conversation_id,
            initiator_id=initiator_id,
            call_type=payload.call_type,
            status=CallStatusEnum.initiated,
            # Store Agora channel name in the existing signaling_metadata JSON column
            signaling_metadata={"channel_name": payload.channel_name},
        )
        await self.repo.create_session(new_call)
        return new_call

    async def add_participant(self, payload: CallParticipantCreate, user_id: str):
        new_participant = CallParticipant(
            call_session_id=payload.call_session_id,
            user_id=user_id,
            muted=payload.muted,
            role=payload.role,
            joined_at=datetime.now(timezone.utc),
        )
        await self.repo.add_participant(new_participant)
        return new_participant

    async def update_status(self, session_id, status, db):
        call = await self.repo.get_session_by_id(session_id)
        if not call:
            raise ValueError("Call session not found")
        await self.repo.update_status(call, status)
        call.ended_at = datetime.now(timezone.utc)
        return call

    async def add_recording(self, payload: CallRecordingCreate):
        recording = CallRecording(
            call_session_id=payload.call_session_id,
            s3_key=payload.s3_key,
            size_bytes=payload.size_bytes,
            duration_seconds=payload.duration_seconds,
        )
        await self.repo.add_recording(recording)
        return recording
