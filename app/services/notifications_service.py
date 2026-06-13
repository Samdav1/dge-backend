import uuid
from datetime import datetime, timezone
from app.repositories.notifications_repo import NotificationRepository
from app.models.notifications import Notification
from app.schemas.notifications import NotificationCreate, NotificationUpdate


class NotificationService:
    def __init__(self, repo: NotificationRepository):
        self.repo = repo

    async def create_notification(self, data: NotificationCreate, user_id: uuid.UUID) -> Notification:
        notification = Notification(
            user_id=data.user_id,
            actor_id=user_id,
            price_negotiation_id=data.price_negotiation_id,
            type=data.type,
            message=data.message,
            metadataInfo=data.metadataInfo,
            created_at=datetime.now(timezone.utc),
        )
        return await self.repo.create(notification)

    async def get_notifications(self, user_id: uuid.UUID) -> list[Notification]:
        return await self.repo.get_by_user(user_id)

    async def mark_as_read(self, notification_id: uuid.UUID) -> Notification | None:
        notification = await self.repo.get(notification_id)
        if not notification:
            return None
        return await self.repo.mark_read(notification)

    async def delete_notification(self, notification_id: uuid.UUID) -> bool:
        notification = await self.repo.get(notification_id)
        if not notification:
            return False
        await self.repo.delete(notification)
        return True