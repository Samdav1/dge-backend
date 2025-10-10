import secrets
from datetime import timezone, datetime, timedelta

from fastapi import HTTPException
from starlette import status
from app.models import RefreshToken
from sqlmodel.ext.asyncio.session import AsyncSession
from app.schemas.user import UserLogin, UserRead, UserToken
from passlib.hash import pbkdf2_sha256 as decrypt
from app.repositories.user_repo import get_user, get_user_token
from app.repositories.refresh_token_repo import create, revoke
import os
from dotenv import load_dotenv
from app.core.security import get_refresh_token

load_dotenv()

REFRESH_TOKEN_EXPIRY_DAYS = os.getenv("REFRESH_TOKEN_EXPIRE_DAYS")

async def login(user_info: UserLogin, db):
    user_detail = await get_user(user_info, db)
    if not user_detail:
        return False
    elif not decrypt.verify(user_info.password, user_detail.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect password")
    else:
     return UserRead.model_validate(user_detail)

async def token_login(user_info: UserToken, db):
    user_detail = await get_user_token(user_info, db)
    if not user_detail:
        return False
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