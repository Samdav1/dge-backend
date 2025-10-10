import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession
from app.db.session import get_session
from app.repositories.notifications_repo import NotificationRepository
from app.services.notifications_service import NotificationService
from app.schemas.notifications import NotificationCreate, NotificationRead
from app.schemas.user import UserRead
from app.dependencies.auth import get_current_user

router = APIRouter(prefix="/notifications",)


@router.post("/", response_model=NotificationRead)
async def create_notification(
    payload: NotificationCreate,
    user: UserRead = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    service = NotificationService(NotificationRepository(db))
    return await service.create_notification(payload, user.id)


@router.get("/", response_model=list[NotificationRead])
async def get_notifications(
    user: UserRead = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    service = NotificationService(NotificationRepository(db))
    return await service.get_notifications(user.id)


@router.put("/{notification_id}/read", response_model=NotificationRead)
async def mark_as_read(
    notification_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
):
    service = NotificationService(NotificationRepository(db))
    notification = await service.mark_as_read(notification_id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    return notification


@router.delete("/{notification_id}", response_model=dict)
async def delete_notification(
    notification_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
):
    service = NotificationService(NotificationRepository(db))
    success = await service.delete_notification(notification_id)
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"message": "Notification deleted successfully"}


