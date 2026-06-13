from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession
from app.db.session import get_session
from app.repositories.presence_repo import PresenceRepository
from app.services.presence_service import PresenceService
from app.schemas.messages import PresenceCreate, PresenceUpdate, PresenceRead
from app.dependencies.auth import get_current_user
from app.schemas.user import UserRead

router = APIRouter(prefix="/presence",)


@router.post("/create_presence", response_model=PresenceRead)
async def create_presence(payload: PresenceCreate, user_id: UserRead = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    service = PresenceService(PresenceRepository(db))
    return await service.create_presence(payload, user_id.id)


@router.get("/get_user_presence", response_model=PresenceRead)
async def get_presence(user_id: UserRead = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    service = PresenceService(PresenceRepository(db))
    return await service.get_presence(user_id.id)


@router.patch("/update_user_presence", response_model=PresenceRead)
async def update_presence(payload: PresenceUpdate,user_id: UserRead = Depends(get_current_user),  db: AsyncSession = Depends(get_session)):
    service = PresenceService(PresenceRepository(db))
    return await service.update_presence(user_id.id, payload)


@router.delete("/delete_user_presence")
async def delete_presence(user_id: UserRead = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    service = PresenceService(PresenceRepository(db))
    return await service.delete_presence(user_id.id)