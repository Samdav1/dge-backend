from fastapi import HTTPException

from app.schemas.profile import ProfileCreate, ProfileRead, ProfileUpdate
from sqlmodel.ext.asyncio.session import AsyncSession
from app.repositories.profile_repo import insert_profile_into_db, update_user_profile

async def create_profile(db: AsyncSession, profile_create: ProfileCreate) -> ProfileRead:
    new_profile = await insert_profile_into_db(db, profile_create)
    return new_profile

async def update_user_profile_service(db: AsyncSession, profile: ProfileUpdate, user_id) -> ProfileRead:
    updated_profile = await update_user_profile(db=db, profile=profile, user_id=user_id)
    if not updated_profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return updated_profile