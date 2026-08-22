from fastapi import HTTPException
from starlette.datastructures import UploadFile

from app.schemas.profile import ProfileCreate, ProfileRead, ProfileUpdate
from sqlmodel.ext.asyncio.session import AsyncSession
from app.repositories.profile_repo import insert_profile_into_db, update_user_profile

from app.repositories.user_repo import get_user_by_id
from app.services.email_notification_service import NotificationService

async def create_profile(db: AsyncSession, profile_create: ProfileCreate, avatar_file: UploadFile, user_id) -> ProfileRead:
    new_profile = await insert_profile_into_db(db, profile_create, avatar_file, user_id)
    if new_profile:
        try:
            user = await get_user_by_id(user_id, db)
            if user:
                notifier = NotificationService()
                notifier.send_profile_updated_mail(
                    user=user,
                    first_name=profile_create.first_name,
                    last_name=profile_create.last_name,
                    phone=profile_create.phone,
                    country=profile_create.country
                )
        except Exception as e:
            print(f"Failed to dispatch profile created email: {e}")
    return new_profile

async def update_user_profile_service(db: AsyncSession, profile: ProfileUpdate, user_id, avatar_file) -> ProfileRead:
    updated_profile = await update_user_profile(db=db, profile=profile, user_id=user_id, avatar_file=avatar_file)
    if not updated_profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    try:
        user = await get_user_by_id(user_id, db)
        if user:
            notifier = NotificationService()
            notifier.send_profile_updated_mail(
                user=user,
                first_name=getattr(updated_profile, 'first_name', None),
                last_name=getattr(updated_profile, 'last_name', None),
                phone=getattr(updated_profile, 'phone', None),
                country=getattr(updated_profile, 'country', None)
            )
    except Exception as e:
        print(f"Failed to dispatch profile updated email: {e}")
    return updated_profile