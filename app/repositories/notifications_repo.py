import uuid
from datetime import datetime, timezone

from sqlalchemy.future import select
from sqlmodel.ext.asyncio.session import AsyncSession
from app.models.notifications import Notification


class NotificationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, notification: Notification) -> Notification:
        self.db.add(notification)
        await self.db.commit()
        await self.db.refresh(notification)
        return notification

    async def get(self, notification_id: uuid.UUID) -> Notification | None:
        result = await self.db.exec(select(Notification).where(Notification.id == notification_id))
        return result.scalar_one_or_none()

    async def get_by_user(self, user_id: uuid.UUID) -> list[Notification]:
        result = await self.db.exec(
            select(Notification).where(Notification.user_id == user_id).order_by(Notification.created_at.desc())
        )
        return result.scalars().all()

    async def mark_read(self, notification: Notification) -> Notification:
        notification.is_read = True
        notification.read_at = notification.read_at or datetime.now(timezone.utc)
        self.db.add(notification)
        await self.db.commit()
        await self.db.refresh(notification)
        return notification

    async def delete(self, notification: Notification) -> None:
        await self.db.delete(notification)
        await self.db.commit()