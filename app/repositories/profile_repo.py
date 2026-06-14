from app.models.profile import Profile
from sqlmodel.ext.asyncio.session import AsyncSession
from app.schemas.profile import ProfileCreate, ProfileRead, ProfileUpdate
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException, UploadFile
from sqlalchemy import select
from app.dependencies.file_handler import save_avatar


async def insert_profile_into_db(db: AsyncSession, profile_create: ProfileCreate,
                                 avatar_file: UploadFile, user_id) -> ProfileRead | None:
    avatar_path = await save_avatar(avatar_file)
    if avatar_path is not None:
        profile_create.avatar_url = avatar_path
    try:
        profile = profile_create.model_dump(exclude_unset=True)
        new_profile = Profile(
            user_id=user_id,
            first_name="",
            last_name="",
            country=""
        )
        for k, v in profile.items():
            setattr(new_profile, k, v)
        db.add(new_profile)
        await db.commit()
        await db.refresh(new_profile)
        refined_profile = ProfileRead.model_validate(new_profile)
        return refined_profile
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"{str(e)}, Error creating profile")

async def update_user_profile(db: AsyncSession, profile: ProfileUpdate, user_id,
                              avatar_file) -> ProfileRead | None:
    statement = select(Profile).where(Profile.user_id == user_id)
    avatar_path = await save_avatar(avatar_file)
    if avatar_path is not None:
        profile.avatar_url = avatar_path
    result = await db.exec(statement)
    user_profile = result.scalars().first()
    
    if not user_profile:
        # If it doesn't exist, create a new profile with defaults
        user_profile = Profile(
            user_id=user_id,
            first_name="",
            last_name="",
            country=""
        )
        db.add(user_profile)

    profile_data = profile.model_dump(exclude_unset=True)
    for key, value in profile_data.items():
        if hasattr(user_profile, key):
            setattr(user_profile, key, value)
            
    # Ensure non-null fields have at least empty strings if they are None or not set
    if user_profile.first_name is None:
        user_profile.first_name = ""
    if user_profile.last_name is None:
        user_profile.last_name = ""
    if user_profile.country is None:
        user_profile.country = ""

    try:
        db.add(user_profile)
        await db.commit()
        await db.refresh(user_profile)
        refined_profile = ProfileRead.model_validate(user_profile)
        return refined_profile
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"{str(e)}, Error updating profile")

