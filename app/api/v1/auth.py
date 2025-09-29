from datetime import timezone
from app.dependencies.auth import get_current_user
from fastapi import APIRouter, HTTPException, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel.ext.asyncio.session import AsyncSession
from app.schemas.user import *
from sqlmodel import SQLModel, Session
from fastapi import Depends
from app.db.session import get_session
from app.services.auth_service import login
from app.core.security import get_access_token
from app.repositories.refresh_token_repo import get_by_token, revoke
from app.services.auth_service import rotate_refresh_token
from app.services.auth_service import issue_refresh_token
import asyncio
from pydantic import json


router = APIRouter()

@router.post("/login", deprecated=True)
async def user_login(user_ifo: UserLogin, db: Session=Depends(get_session) ):
    # return await login(user_ifo, db)
    return {"message": "This endpoint is deprecated. Use /token instead."}

@router.post("/token")
async def login_for_access_token(response: Response, form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_session)):
    user_ifo = UserLogin.model_validate({
        "username": form_data.username,
        "password": form_data.password
    })
    data = await login(user_ifo, db)
    id_value = str(data.id)
    token = await get_access_token(subject=id_value)
    refresh_token = await issue_refresh_token(user_id=id_value, db=db)

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=7 * 24 * 60 * 60
    )

    return {"access_token": token, "token_type": "bearer", "user": data}


@router.post("/refresh")
async def refresh_tokens(refresh_token: str, db: AsyncSession = Depends(get_session)):
    db_token = await get_by_token(db, refresh_token)
    if not db_token or db_token.revoked or db_token.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    new_refresh = await rotate_refresh_token(db, refresh_token, db_token.user_id)
    new_access_token = "generate_new_access_here"  # <- plug your JWT function

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh.token
    }

@router.post("/logout")
async def logout(refresh_token: str, db: AsyncSession = Depends(get_session)):
    token = await revoke(db, refresh_token)
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")
    return {"message": "Logged out successfully"}