from typing import Union

from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from app.models.user import Users
from app.schemas.user import UserCreate, UserLogin, UserToken, UserGoogleCreate


async def create_user(db: AsyncSession, user: Union[UserCreate, UserGoogleCreate], password: str = None) -> Users:
    try:
        new_user = Users(
            username=user.username,
            email=user.email,
            password=password,
            google_auth=user.google_auth
        )
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        return new_user
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"DB error: {str(e)}")


async def get_user(user_info: UserLogin, db: AsyncSession):
    stmt = select(Users).where(Users.email == user_info.username)
    result = await db.exec(stmt)
    user = result.first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


async def get_user_token(user_info: UserToken, db: AsyncSession,):
    stmt = select(Users).where(Users.username == user_info.username)
    result = await db.exec(stmt)
    user = result.first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


async def get_user_by_id(user_id, db: AsyncSession):
    stmt = select(Users).where(Users.id == user_id)
    result = await db.exec(stmt)
    user = result.first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user

async def get_user_by_email(email: str, db: AsyncSession):
    stmt = select(Users).where(Users.email == email)
    result = await db.exec(stmt)
    user = result.first()
    if user is None:
        return None
    return user