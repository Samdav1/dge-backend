import uuid
from app.repositories.location_repo import LocationRepository
from app.models.user import Locations
from app.schemas.location import LocationCreate, LocationUpdate


class LocationService:
    def __init__(self, repo: LocationRepository, user_id):
        self.repo = repo
        self.user_id = user_id
    async def create_location(self, data: LocationCreate) -> Locations:
        location = Locations(**data.model_dump(), user_id=self.user_id)
        return await self.repo.create(location)

    async def get_location(self, location_id: uuid.UUID) -> Locations | None:
        return await self.repo.get(location_id)

    async def get_locations_by_user(self, user_id: uuid.UUID) -> list[Locations]:
        return await self.repo.get_by_user(user_id)

    async def get_all_locations(self) -> list[Locations]:
        return await self.repo.get_all()

    async def update_location(self, location_id: uuid.UUID, data: LocationUpdate) -> Locations | None:
        location = await self.repo.get(location_id)
        if not location:
            return None
        for field, value in data.dict(exclude_unset=True).items():
            setattr(location, field, value)
        return await self.repo.update(location)

    async def delete_location(self, location_id: uuid.UUID) -> bool:
        location = await self.repo.get(location_id)
        if not location:
            return False
        await self.repo.delete(location)
        return True
