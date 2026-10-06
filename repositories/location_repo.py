import uuid
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.future import select
from app.models.user import Locations


class LocationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, location: Locations) -> Locations:
        self.db.add(location)
        await self.db.commit()
        await self.db.refresh(location)
        return location

    async def get(self, location_id: uuid.UUID) -> Locations | None:
        result = await self.db.exec(select(Locations).where(Locations.id == location_id))
        return result.scalar_one_or_none()

    async def get_by_user(self, user_id: uuid.UUID) -> list[Locations]:
        result = await self.db.exec(select(Locations).where(Locations.user_id == user_id))
        return result.scalars().all()

    async def get_all(self) -> list[Locations]:
        result = await self.db.exec(select(Locations))
        return result.scalars().all()

    async def update(self, location: Locations) -> Locations:
        self.db.add(location)
        await self.db.commit()
        await self.db.refresh(location)
        return location

    async def delete(self, location: Locations) -> None:
        await self.db.delete(location)
        await self.db.commit()
