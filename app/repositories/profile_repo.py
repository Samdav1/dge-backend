from app.models.profile import Profile
from sqlmodel.ext.asyncio.session import AsyncSession
from app.schemas.profile import ProfileCreate, ProfileRead, ProfileUpdate
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException
from sqlalchemy import select


async def insert_profile_into_db(db: AsyncSession, profile_create: ProfileCreate) -> ProfileRead | None:
    try:
        profile = Profile(user_id= profile_create.user_id)
        db.add(profile)
        await db.commit()
        await db.refresh(profile)
        refined_profile = ProfileRead.model_validate(profile)
        return refined_profile
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"{str(e)}, Error creating profile")

async def update_user_profile(db: AsyncSession, profile: ProfileUpdate, user_id: str) -> ProfileRead | None:
    statement = select(Profile).where(Profile.user_id == user_id)
    result = await db.exec(statement)
    user_profile = result.scalars().first()
    if not user_profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    profile_data = profile.model_dump(exclude_unset=True)
    for key, value in profile_data.items():
        if hasattr(user_profile, key):
            setattr(user_profile, key, value)
    try:
        db.add(user_profile)
        await db.commit()
        await db.refresh(user_profile)
        refined_profile = ProfileRead.model_validate(user_profile)
        return refined_profile
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"{str(e)}, Error updating profile")
