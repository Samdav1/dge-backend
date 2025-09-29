from typing import Literal, Optional, Union

from fastapi import APIRouter, Depends, Response
from sqlmodel import Session
from app.db.session import get_session
from app.schemas.user import UserCreate, UserRead
from app.services.auth_service import issue_refresh_token
from app.services.user_service import create_user_service
from pydantic.main import Union
from sqlmodel.ext.asyncio.session import AsyncSession
from app.core.security import get_access_token

from app import schemas

router = APIRouter()


@router.get("/")
async def get_users():
    return {'user': ['samuel', 'Esther', 'Solomon']}


@router.post("/user-signup",)
async def create(response: Response, user_create: UserCreate, referrals: str | None = None, db: AsyncSession = Depends(get_session)):
    user = await create_user_service(db=db, user=user_create)
    refresh_token = await issue_refresh_token(user_id=str(user["user"].id), db=db)

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite= "lax",
        max_age=7*24*60*60
    )
    return user
