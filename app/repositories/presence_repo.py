from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy import select
from app.models.messages import Presence
from app.schemas.messages import PresenceCreate, PresenceUpdate, PresenceRead


class PresenceRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_presence(self, payload: PresenceCreate, user_id) -> Presence:
        presence = Presence(**payload.dict(), user_id=user_id)
        self.db.add(presence)
        await self.db.commit()
        await self.db.refresh(presence)
        return presence

    async def get_presence(self, user_id) -> Presence | None:
        result = await self.db.exec(select(Presence).where(Presence.user_id == user_id))
        presence = result.scalar()
        return presence

    async def update_presence(self, user_id, payload: PresenceUpdate) -> Presence | None:
        presence = await self.get_presence(user_id)
        if not presence:
            return None

        for key, value in payload.dict(exclude_unset=True).items():
            setattr(presence, key, value)

        await self.db.commit()
        await self.db.refresh(presence)
        return presence

    async def delete_presence(self, user_id) -> bool:
        presence = await self.get_presence(user_id)
        if not presence:
            return False

        await self.db.delete(presence)
        await self.db.commit()
        return True
