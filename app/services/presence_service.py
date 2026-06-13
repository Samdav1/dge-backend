from fastapi import HTTPException
from app.repositories.presence_repo import PresenceRepository
from app.schemas.messages import PresenceCreate, PresenceUpdate, PresenceRead


class PresenceService:
    def __init__(self, repo: PresenceRepository):
        self.repo = repo

    async def create_presence(self, payload: PresenceCreate, user_id: str) -> PresenceRead:
        presence = await self.repo.create_presence(payload, user_id)
        return PresenceRead.model_validate(presence)

    async def get_presence(self, user_id) -> PresenceRead:
        presence = await self.repo.get_presence(user_id)
        if not presence:
            raise HTTPException(status_code=404, detail="Presence not found")
        return PresenceRead.model_validate(presence)

    async def update_presence(self, user_id, payload: PresenceUpdate) -> PresenceRead:
        presence = await self.repo.update_presence(user_id, payload)
        if not presence:
            raise HTTPException(status_code=404, detail="Presence not found")
        return PresenceRead.model_validate(presence)

    async def delete_presence(self, user_id) -> dict:
        deleted = await self.repo.delete_presence(user_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Presence not found")
        return {"detail": "Presence deleted"}
