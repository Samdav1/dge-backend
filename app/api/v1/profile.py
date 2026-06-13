import uuid
from datetime import datetime, date
from typing import Optional

from app.services.profile_service import create_profile, update_user_profile_service
from fastapi import APIRouter, Depends, HTTPException, Request, File, UploadFile, Form
from sqlmodel.ext.asyncio.session import AsyncSession
from app.db.session import get_session
from app.schemas.profile import ProfileCreate, ProfileRead, ProfileUpdate
from app.dependencies.auth import get_current_user

from app.models.profile import Profile
from sqlalchemy import select

router = APIRouter()

@router.get("/get_profile", response_model=ProfileRead, dependencies=[Depends(get_current_user)])
async def get_current_user_profile(
        request: Request,
        db: AsyncSession = Depends(get_session)):
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid access token payload")

    statement = select(Profile).where(Profile.user_id == user_id)
    result = await db.exec(statement)
    user_profile = result.scalars().first()
    if not user_profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    return ProfileRead.model_validate(user_profile)

@router.post("/create_profile", response_model=ProfileRead, dependencies=[Depends(get_current_user)])
async def create_new_profile(
        request: Request,
        first_name: Optional[str] = Form(None),
        last_name: Optional[str] = Form(None),
        date_of_birth: Optional[str] = Form(None), # Input as string
        gender: Optional[str] = Form(None),
        phone: Optional[str] = Form(None),
        address_line1: Optional[str] = Form(None),
        address_line2: Optional[str] = Form(None),
        city: Optional[str] = Form(None),
        state: Optional[str] = Form(None),
        postal_code: Optional[str] = Form(None),
        country: Optional[str] = Form(None),
        bio: Optional[str] = Form(None),
        team_id: Optional[str] = Form(None),
        avatar_file: Optional[UploadFile] = File(None),
        db: AsyncSession = Depends(get_session)):
    form_params = {
        "first_name": first_name, "last_name": last_name, "gender": gender,
        "phone": phone, "address_line1": address_line1, "address_line2": address_line2,
        "city": city, "state": state, "postal_code": postal_code, "country": country,
        "bio": bio
    }
    creation_data = {key: value for key, value in form_params.items() if value is not None}

    if date_of_birth not in [None, "", "null", "undefined"]:
        try:
            creation_data["date_of_birth"] = date.fromisoformat(date_of_birth)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format for date_of_birth. Use YYYY-MM-DD.")

    if team_id not in [None, "", "null", "undefined"]:
        try:
            creation_data["team_id"] = uuid.UUID(team_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid team_id format. Must be a UUID.")
    try:
        profile_create_payload = ProfileCreate(**creation_data)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Data validation failed: {e}")
    try:
        user_id = getattr(request.state, "user_id", None)
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid user ID.")

    new_profile = await create_profile(db, profile_create_payload, avatar_file, user_id)
    if not new_profile:
        raise HTTPException(status_code=400, detail="Profile could not be created")
    return new_profile


@router.patch("/update_profile", response_model=ProfileRead, dependencies=[Depends(get_current_user)])
async def update_profile(
        request: Request,
        first_name: Optional[str] = Form(None),
        last_name: Optional[str] = Form(None),
        date_of_birth: Optional[str] = Form(None),  # Input as string
        gender: Optional[str] = Form(None),
        phone: Optional[str] = Form(None),
        address_line1: Optional[str] = Form(None),
        address_line2: Optional[str] = Form(None),
        city: Optional[str] = Form(None),
        state: Optional[str] = Form(None),
        postal_code: Optional[str] = Form(None),
        country: Optional[str] = Form(None),
        bio: Optional[str] = Form(None),
        team_id: Optional[str] = Form(None),
        avatar_file: Optional[UploadFile] = File(None),
        db: AsyncSession = Depends(get_session)):
    form_params = {
        "first_name": first_name, "last_name": last_name, "gender": gender,
        "phone": phone, "address_line1": address_line1, "address_line2": address_line2,
        "city": city, "state": state, "postal_code": postal_code, "country": country,
        "bio": bio
    }
    creation_data = {key: value for key, value in form_params.items() if value is not None}

    # 2. Handle type conversions (string -> date, string -> UUID)
    if date_of_birth not in [None, "", "null", "undefined"]:
        try:
            creation_data["date_of_birth"] = date.fromisoformat(date_of_birth)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format for date_of_birth. Use YYYY-MM-DD.")

    if team_id not in [None, "", "null", "undefined"]:
        try:
            creation_data["team_id"] = uuid.UUID(team_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid team_id format. Must be a UUID.")


    try:
        profile_create_payload = ProfileUpdate(**creation_data)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Data validation failed: {e}")
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid access token payload, not valid")
    try:
        updated_profile = await update_user_profile_service(db=db, profile=profile_create_payload, user_id=user_id, avatar_file=avatar_file)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"{e}, Profile not found")
    return updated_profile