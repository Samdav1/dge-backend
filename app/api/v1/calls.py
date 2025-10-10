# app/api/v1/endpoints/call.py

from fastapi import APIRouter, Depends, status
from sqlmodel.ext.asyncio.session import AsyncSession
from app.db.session import get_session
from app.schemas.call import (
    CallSessionCreate,
    CallSessionRead,
    CallParticipantCreate,
    CallRecordingCreate,
)
from app.repositories.call_repo import CallRepository
from app.services.call_service import CallService
from app.dependencies.auth import get_current_user

router = APIRouter(prefix="/calls", )


@router.post("/create", response_model=CallSessionRead, status_code=status.HTTP_201_CREATED)
async def create_call_session(
    payload: CallSessionCreate,
    db: AsyncSession = Depends(get_session),
    user=Depends(get_current_user)
):
    service = CallService(CallRepository(db))
    call = await service.create_call(payload, initiator_id=user.id)
    await db.commit()
    await db.refresh(call)
    return call


@router.post("/add_participant", status_code=status.HTTP_201_CREATED)
async def add_call_participant(
    payload: CallParticipantCreate,
    db: AsyncSession = Depends(get_session),
    user=Depends(get_current_user)
):
    service = CallService(CallRepository(db))
    participant = await service.add_participant(payload, user.id)
    await db.commit()
    await db.refresh(participant)
    return participant


@router.patch("/{call_id}/status/{status}")
async def update_call_status(
    call_id: str,
    status: str,
    db: AsyncSession = Depends(get_session)
):
    service = CallService(CallRepository(db))
    call = await service.update_status(call_id, status, db)
    await db.commit()
    await db.refresh(call)
    return call


@router.post("/recording/upload", status_code=status.HTTP_201_CREATED)
async def upload_call_recording(
    payload: CallRecordingCreate,
    db: AsyncSession = Depends(get_session)
):
    service = CallService(CallRepository(db))
    recording = await service.add_recording(payload)
    await db.commit()
    await db.refresh(recording)
    return recording
