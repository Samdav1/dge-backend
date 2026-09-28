from fastapi.concurrency import run_in_threadpool
from app.models import Users
from app.repositories.user_repo import create_user, get_user_by_email, get_user_by_referral_code
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
    
    if user.referral_code:
        referrer = await get_user_by_referral_code(user.referral_code, db)
        if referrer:
            user_info.referred_by_id = referrer.id
            db.add(user_info)
            await db.commit()
            await db.refresh(user_info)

    user_read = UserRead.model_validate(user_info)
    token = await get_access_token(str(user_read.id))

    """Creating User Wallet Service"""
    if not await get_user_wallet_service(db, user_read.id):
        await create_user_wallet_service(db, user_read.id)

    # Initialize user DGE Points with sign up bonus (10 points)
    from app.services.points_service import get_or_create_user_points
    await get_or_create_user_points(db, user_read.id)

    notification_service = NotificationService()
    notification_service.send_signup_welcome_mail(user_read)

    try:
        from app.services.auth_service import create_user_email_verification_token
        await create_user_email_verification_token(user_read.email, db)
    except Exception as e:
        print(f"Failed to dispatch verification email: {e}")

    return {"user": user_read, "access_token": token}

async def google_auth_login(token: GoogleCallBack, db: AsyncSession):
    """

    :param token:
    :param db:
    :return:
    """
    user_info = id_token.verify_oauth2_token(
        token.id_token,
        requests.Request(),
        GOOGLE_CLIENT_ID, clock_skew_in_seconds=10
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
        GOOGLE_CLIENT_ID, clock_skew_in_seconds=10
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
        
        if referral_code:
            referrer = await get_user_by_referral_code(referral_code, db)
            if referrer:
                user_info.referred_by_id = referrer.id
                db.add(user_info)
                await db.commit()
                await db.refresh(user_info)

        user = UserRead.model_validate(user_info)
        token = await get_access_token(str(user.id))

        """Creating User Wallet Service"""
        if not await get_user_wallet_service(db, user.id):
            await create_user_wallet_service(db, user.id)

        # Initialize user DGE Points with sign up bonus (10 points)
        from app.services.points_service import get_or_create_user_points
        await get_or_create_user_points(db, user.id)

        notification_service = NotificationService()
        notification_service.send_signup_welcome_mail(user)

        return {"user": user, "access_token": token}