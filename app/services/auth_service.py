import secrets
from datetime import timezone, datetime, timedelta

from fastapi import HTTPException
from pydantic import EmailStr
from starlette import status
from app.models import RefreshToken
from sqlmodel.ext.asyncio.session import AsyncSession
from app.schemas.user import UserLogin, UserRead, UserToken
from passlib.hash import pbkdf2_sha256 as decrypt
from app.repositories.user_repo import get_user, get_user_token, get_user_by_id, get_user_by_email
from app.repositories.refresh_token_repo import create, revoke
import os
from dotenv import load_dotenv
from app.core.security import get_refresh_token, create_email_token, decode_email_token
from app.schemas.auth import  ChangeUserPass
from app.services.email_notification_service import NotificationService

from app.models.user import Users
from app.repositories.team_repo import TeamRepository
from app.schemas.team import TeamUserRead
load_dotenv()

REFRESH_TOKEN_EXPIRY_DAYS = os.getenv("REFRESH_TOKEN_EXPIRE_DAYS")

async def login(user_info: UserLogin, db):
    user_detail = await get_user(user_info, db)
    if not user_detail:
        return False
    elif not user_detail.password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect password")
    elif not decrypt.verify(user_info.password, user_detail.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect password")
    else:
        return UserRead.model_validate(user_detail)


async def team_login(user_info: UserLogin, db):
    team_repo = TeamRepository(db)
    user_detail = await team_repo.get_team_user_by_email(user_info.username)
    if not user_detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team member not found")
    elif not decrypt.verify(user_info.password, user_detail.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect password")
    else:
        return TeamUserRead.model_validate(user_detail)


async def token_login(user_info: UserToken, db):
    user_detail = await get_user_token(user_info, db)
    if not user_detail:
        return False
    elif not user_detail.password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect password")
    elif not decrypt.verify(user_info.password, user_detail.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect password")
    else:
     return UserRead.model_validate(user_detail)

async def issue_refresh_token(db: AsyncSession, user_id: str):
    """

    :param db:
    :param user_id:
    :return:
    """
    token = await get_refresh_token(subject=user_id)
    expires_at = datetime.now(timezone.utc) + timedelta(days=int(REFRESH_TOKEN_EXPIRY_DAYS))

    refresh_token = RefreshToken(
        user_id=user_id,
        token=token,
        expires_at=expires_at
    )
    return await create(db, refresh_token)

async def rotate_refresh_token(db: AsyncSession, old_token: str, user_id: str):
    await revoke(db, old_token)
    return await issue_refresh_token(db, user_id)

async def create_user_email_verification_token(user: UserRead, db: AsyncSession):
    from jose import JWTError
    try:
        token = await  create_email_token(str(user.id))
    except JWTError as e:
        raise HTTPException(detail=str(e), status_code=status.HTTP_401_UNAUTHORIZED)

    notifier = NotificationService()

    notifier.send_verification_email(new_user=user, token=token)

async def verify_user_email_verification_token(token: str, db: AsyncSession):
    """

    :param token:
    :param db:
    """
    from jose import JWTError
    try:
        payload = await decode_email_token(token)
    except JWTError as e:
        raise HTTPException(detail=str(e), status_code=status.HTTP_401_UNAUTHORIZED)

    if payload.get("sub"):
        user_id = payload["sub"]
        user = await get_user_by_id(user_id, db)
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User Not found")

        user.email_verified = True
        db.add(user)
        await db.commit()
        await db.refresh(user)
        notifier = NotificationService()
        notifier.send_verification_success_email(user)
    else:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

async def send_password_reset_link_service(email: EmailStr, db: AsyncSession):
    """
    :param email:
    :param db:
    :return:
    """
    if email:
        user = await get_user_by_email(str(email), db)
        if user:
            token = await create_email_token(str(user.id))
            notifier = NotificationService()
            notifier.send_verification_email(user, token)
            return {"message": "Password Reset Link Successfully Sent!"}
        else:
            raise HTTPException(status_code=404, detail="Email not found")
    else:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Invalid email credentials")

async def change_user_pass_service(user_pass: ChangeUserPass, db: AsyncSession):
    """

    :param user_pass:
    :param db:
    :return:
    """
    if user_pass:
        from jose import JWTError
        try:
            payload = await decode_email_token(user_pass.token)

        except Exception as e:
            raise HTTPException(detail=str(e), status_code=status.HTTP_401_UNAUTHORIZED)

        if payload.get("sub"):
            user_id = payload["sub"]
            user = await get_user_by_id(user_id, db)
            if not user:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User Not found")

            user.password = user_pass.password
            db.add(user)
            await db.commit()
            await db.refresh(user)
            notifier = NotificationService()
            notifier.send_verification_success_email(user)
        else:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    return {"message": "Password Change Successfully"}

async def send_team_password_reset_link_service(email: EmailStr, db: AsyncSession):
    if email:
        team_repo = TeamRepository(db)
        user = await team_repo.get_team_user_by_email(str(email))
        if user:
            token = await create_email_token(str(user.id))
            notifier = NotificationService()
            notifier.send_verification_email(user, token)
            return {"message": "Password Reset Link Successfully Sent!"}
        else:
            raise HTTPException(status_code=404, detail="Email not found")
    else:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Invalid email credentials")

async def change_team_user_pass_service(user_pass: ChangeUserPass, db: AsyncSession):
    if user_pass:
        from jose import JWTError
        try:
            payload = await decode_email_token(user_pass.token)
        except Exception as e:
            raise HTTPException(detail=str(e), status_code=status.HTTP_401_UNAUTHORIZED)

        if payload.get("sub"):
            user_id = payload["sub"]
            team_repo = TeamRepository(db)
            user = await team_repo.get_team_user(user_id)
            if not user:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User Not found")

            user.password_hash = decrypt.hash(user_pass.password)
            db.add(user)
            await db.commit()
            await db.refresh(user)
            notifier = NotificationService()
            notifier.send_verification_success_email(user)
        else:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    return {"message": "Password Change Successfully"}