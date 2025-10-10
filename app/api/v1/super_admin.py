# app/api/v1/superadmin.py
from fastapi import APIRouter, Depends, UploadFile, Form, status, Response
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import Optional, List
import uuid

from watchfiles.run import get_tty_path

from app.core.security import get_access_token, get_refresh_token
from app.dependencies.admin_auth import get_current_admin
from app.services.super_admin_service import SuperAdminService
from app.models.admin import AdminRank
from app.schemas.super_admin import SuperAdminRead, AdminLogin, SuperAdminLoginRead
from app.db.session import get_session
from fastapi.security import OAuth2PasswordRequestForm

router = APIRouter(prefix="/super_admins")
service = SuperAdminService()


@router.post("/",  status_code=status.HTTP_201_CREATED)
async def create_superadmin(
        response: Response,
        name: str = Form(...),
        email: str = Form(...),
        password: str = Form(...),
        phone_number: Optional[str] = Form(None),
        rank: AdminRank = Form(AdminRank.Major),
        avatar: Optional[UploadFile] = None,
        session: AsyncSession = Depends(get_session),
):
    """Create a new SuperAdmin (multipart form with image upload)."""
    new_admin = await service.create_superadmin(session, name, email, password, phone_number, rank, avatar)
    access_token = await get_access_token(str(new_admin.id))
    refresh_token = await get_refresh_token(str(new_admin.id))
    admin_refined = SuperAdminLoginRead.model_validate(new_admin)

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        samesite="Lax",
        secure=True,
        max_age=7 * 24 * 60 * 60,
    )

    return {"admin": admin_refined, "access_token": access_token}


@router.get("/", response_model=List[SuperAdminRead])
async def list_superadmins(session: AsyncSession = Depends(get_session), get_admin: SuperAdminRead = Depends(get_current_admin)):
    return await service.list_superadmins(session)


@router.get("/{admin_id}", response_model=SuperAdminRead)
async def get_superadmin(admin_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    return await service.get_superadmin(session, admin_id)


@router.delete("/{admin_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_superadmin(admin_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    await service.delete_superadmin(session, admin_id)
    return None

@router.post("/login")
async def login(
        response: Response,
        db: AsyncSession = Depends(get_session),
        form_data: OAuth2PasswordRequestForm = Depends()):
    admin_info = AdminLogin.model_validate({"username": form_data.username, "password": form_data.password})
    admin_details = await service.admin_login(db, admin_info)

    access_token = await get_access_token(str(admin_details.id))
    refresh_token = await get_refresh_token(str(admin_details.id))
    admin_refined = SuperAdminLoginRead.model_validate(admin_details)

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        samesite="Lax",
        secure=True,
        max_age=7 * 24 * 60 * 60,
    )

    return {"admin": admin_refined, "access_token": access_token}