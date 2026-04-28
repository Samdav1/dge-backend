from fastapi.concurrency import run_in_threadpool
from app.models import Users
from app.repositories.user_repo import create_user, get_user_by_email
from passlib.hash import pbkdf2_sha256 as encrypt
from sqlmodel import select, Session
from sqlmodel.ext.asyncio.session import AsyncSession
from fastapi import HTTPException
from app.schemas.auth import GoogleCallBack
from app.services.auth_service import issue_refresh_token
from app.core.security import get_access_token
from app.schemas.user import UserCreate, UserRead, UserGoogleCreate
from app.services.email_notification_service import NotificationService
from google.oauth2 import id_token
from google.auth.transport import requests
from app.services.wallet_service import create_user_wallet_service, get_user_wallet_service
import os
from dotenv import load_dotenv

load_dotenv()
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

async def create_user_service(db: AsyncSession, user: UserCreate):
    """
    Creates a user, dispatches a welcome email, and returns credentials.
    All blocking calls are handled asynchronously.
    """
    hash_pass = await run_in_threadpool(encrypt.hash, user.password)
    user_info = await create_user(db=db, user=user, password=hash_pass)
    user = UserRead.model_validate(user_info)
    token = await get_access_token(str(user.id))

    """Creating User Wallet Service"""
    if not await get_user_wallet_service(db, user.id):
        await create_user_wallet_service(db, user.id)

    notification_service = NotificationService()
    notification_service.send_signup_welcome_mail(user)

    return {"user": user, "access_token": token}

async def google_auth_login(token: GoogleCallBack, db: AsyncSession):
    """

    :param token:
    :param db:
    :return:
    """
    user_info = id_token.verify_oauth2_token(
        token.id_token,
        requests.Request(),
        GOOGLE_CLIENT_ID,
    )

    user_email = user_info["email"]
    user = await get_user_by_email(db=db, email=user_email)
    if user:
        user_modified = UserRead.model_validate(user)
        token = await get_access_token(str(user.id))
        return {"user": user_modified, "access_token": token}
    else:
        raise HTTPException(status_code=404, detail="User not found")

async def google_auth_signup(token: GoogleCallBack, db: AsyncSession, referral_code: str = None):
    """

    :param referral_code:
    :param token:
    :param db:
    :return:
    """
    user_info = id_token.verify_oauth2_token(
        token.id_token,
        requests.Request(),
        GOOGLE_CLIENT_ID,
    )

    print(user_info)

    user_email = user_info["email"]
    user = await get_user_by_email(db=db, email=user_email)
    if user:
        raise HTTPException(status_code=409, detail="User with email already exists")
    else:
        new_user = UserGoogleCreate(
            email=user_email,
            username=user_info["given_name"],
            referral_code=referral_code,
        )
        user_info = await create_user(db=db, user=new_user)
        user = UserRead.model_validate(user_info)
        token = await get_access_token(str(user.id))

        """Creating User Wallet Service"""
        if not await get_user_wallet_service(db, user.id):
            await create_user_wallet_service(db, user.id)

        notification_service = NotificationService()
        notification_service.send_signup_welcome_mail(user)

        return {"user": user, "access_token": token}