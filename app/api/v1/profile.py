from app.services.profile_service import create_profile, update_user_profile_service
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel.ext.asyncio.session import AsyncSession
from app.db.session import get_session
from app.schemas.profile import ProfileCreate, ProfileRead, ProfileUpdate
from app.dependencies.auth import get_current_user

router = APIRouter()

@router.post("/create_profile", response_model=ProfileRead, dependencies=[Depends(get_current_user)])
async def create_new_profile(
    profile_create: ProfileCreate,
    db: AsyncSession = Depends(get_session)
):
    new_profile = await create_profile(db, profile_create)
    if not new_profile:
        raise HTTPException(status_code=400, detail="Profile could not be created")
    return new_profile

@router.patch("/update_profile", response_model=ProfileRead, dependencies=[Depends(get_current_user)])
async def update_profile(
        request: Request,
        profile: ProfileUpdate,
        db: AsyncSession = Depends(get_session),
):
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid access token payload, not valid")
    try:
        updated_profile = await update_user_profile_service(db=db, profile=profile, user_id=user_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"{e}, Profile not found")
    return updated_profile