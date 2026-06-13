# app/api/v1/endpoints/call.py

from fastapi import APIRouter, Depends, status, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession
from app.db.session import get_session
from app.schemas.call import (
    CallSessionCreate,
    CallSessionRead,
    CallParticipantCreate,
    CallRecordingCreate,
    AgoraTokenRequest,
    AgoraTokenResponse,
)
from app.repositories.call_repo import CallRepository
from app.services.call_service import CallService
from app.services.agora_service import generate_agora_token
from app.dependencies.auth import get_current_user
from app.config import settings

router = APIRouter(prefix="/calls")


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


@router.post("/agora/token", response_model=AgoraTokenResponse)
async def get_agora_token(
    payload: AgoraTokenRequest,
    user=Depends(get_current_user),
):
    """
    Generate a short-lived Agora RTC token for the authenticated user.

    The client should use this token together with the returned `app_id` and
    `channel_name` to join an Agora channel via the Agora Web / Mobile SDK.

    Token validity defaults to 1 hour. The client should request a new token
    using the `onTokenPrivilegeWillExpire` SDK callback before expiry.
    """
    app_id = settings.agora_app_id
    app_cert = settings.agora_app_certificate

    if not app_id or not app_cert:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agora RTC is not configured on the server. Please set AGORA_APP_ID and AGORA_APP_CERTIFICATE.",
        )

    token = generate_agora_token(
        app_id=app_id,
        app_certificate=app_cert,
        channel_name=payload.channel_name,
        uid=payload.uid,
        role=payload.role,
        expire_seconds=payload.expire_seconds,
    )

    return AgoraTokenResponse(
        token=token,
        channel_name=payload.channel_name,
        uid=payload.uid,
        app_id=app_id,
        expires_in=payload.expire_seconds,
    )
