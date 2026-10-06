from datetime import timezone, datetime, timedelta
from app.dependencies.auth import get_current_user
from fastapi import APIRouter, HTTPException, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel.ext.asyncio.session import AsyncSession
from app.schemas.user import *
from sqlmodel import SQLModel, Session
from fastapi import Depends
from app.db.session import get_session
from app.services.auth_service import login, team_login
from app.core.security import get_access_token
from app.repositories.refresh_token_repo import get_by_token, revoke
from app.services.auth_service import rotate_refresh_token, send_password_reset_link_service, change_user_pass_service, send_team_password_reset_link_service, change_team_user_pass_service
from app.services.auth_service import issue_refresh_token
from app.services.user_service import google_auth_login, google_auth_signup, create_user_service
import asyncio
from pydantic import json
from app.schemas.auth import GoogleCallBack, ChangeUserPass
from google.oauth2 import id_token
from google.auth.transport import requests


router = APIRouter()

@router.post("/login", deprecated=True)
async def user_login(user_ifo: UserLogin, db: Session=Depends(get_session) ):
    # return await login(user_ifo, db)
    return {"message": "This endpoint is deprecated. Use /token instead."}

@router.post("/user-signup",)
async def create(response: Response, user_create: UserCreate, referrals: str | None = None,
                 db: AsyncSession = Depends(get_session)):
    user = await create_user_service(db=db, user=user_create)
    refresh_token = await issue_refresh_token(user_id=str(user["user"].id), db=db)

    response.set_cookie(
        key="refresh_token",
        value=refresh_token.token,
        httponly=True,
        secure=True,
        samesite= "lax",
        max_age=7*24*60*60
    )
    return user



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
        value=refresh_token.token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=7 * 24 * 60 * 60
    )

    return {"access_token": token, "token_type": "bearer", "user": data}


@router.post("/team-login")
async def login_for_team_access_token(response: Response, form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_session)):
    user_ifo = UserLogin.model_validate({
        "username": form_data.username,
        "password": form_data.password
    })
    data = await team_login(user_ifo, db)
    id_value = str(data.id)
    token = await get_access_token(subject=id_value)
    refresh_token = await issue_refresh_token(user_id=id_value, db=db)

    response.set_cookie(
        key="refresh_token",
        value=refresh_token.token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=7 * 24 * 60 * 60
    )

    return {"access_token": token, "token_type": "bearer", "user": data}


@router.post("/refresh")
async def refresh_tokens(refresh_token: str, db: AsyncSession = Depends(get_session)):
    db_token = await get_by_token(db, refresh_token)
    if not db_token or db_token.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    # Allow a 30-second grace period for recently revoked tokens to handle race conditions
    if db_token.revoked:
        grace_period = timedelta(seconds=30)
        if not db_token.revoked_at or (datetime.now(timezone.utc) - db_token.revoked_at) > grace_period:
            raise HTTPException(status_code=401, detail="Refresh token has been revoked")

    new_refresh = await rotate_refresh_token(db, refresh_token, db_token.user_id)
    new_access_token = await get_access_token(subject=str(db_token.user_id))

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

@router.post("/login/google/callback")
async def google_callback_login(response: Response, token: GoogleCallBack, db: AsyncSession = Depends(get_session)):
    """

    :param db:
    :param token:
    """
    result = await google_auth_login(token=token, db=db)
    id_value = result["user"]
    refresh_token = await issue_refresh_token(user_id=str(id_value.id), db=db)

    response.set_cookie(
        key="refresh_token",
        value=refresh_token.token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=7 * 24 * 60 * 60
    )
    print(result)
    return result

@router.post("/signup/google/callback")
async def google_callback_signup(token: GoogleCallBack, referral_code: str = None,
                                 db: AsyncSession = Depends(get_session)):
    """

    :param referral_code:
    :param db:
    :param token:
    """
    result = await google_auth_signup(token=token, db=db, referral_code=referral_code)
    print(result)
    return result

@router.post("/change_password_email")
async def send_password_reset_link(email: EmailStr, db: AsyncSession = Depends(get_session)):
    if email:
        response = await send_password_reset_link_service(email=email, db=db)
        return  response
    else:
        from starlette import status
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Invalid email credentials")

@router.put("/change_password")
async def change_user_password(password_info: ChangeUserPass, db: AsyncSession = Depends(get_session)):
    """
    :param password_info:
    :param db:
    """

    if password_info:
        response = await change_user_pass_service(user_pass=password_info, db=db)
        return response
    else:
        from starlette import status
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Invalid password credentials")

@router.post("/team-change_password_email")
async def send_team_password_reset_link(email: EmailStr, db: AsyncSession = Depends(get_session)):
    if email:
        response = await send_team_password_reset_link_service(email=email, db=db)
        return response
    else:
        from starlette import status
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Invalid email credentials")

@router.put("/team-change_password")
async def change_team_password(password_info: ChangeUserPass, db: AsyncSession = Depends(get_session)):
    if password_info:
        response = await change_team_user_pass_service(user_pass=password_info, db=db)
        return response
    else:
        from starlette import status
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Invalid password credentials")