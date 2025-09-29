from app.models import Users
from app.repositories.user_repo import create_user
from passlib.hash import pbkdf2_sha256 as encrypt
from sqlmodel import select, Session
from sqlmodel.ext.asyncio.session import AsyncSession
from app.services.auth_service import issue_refresh_token
from app.core.security import get_access_token

from app.schemas.user import UserCreate, UserRead


async def create_user_service(db: AsyncSession, user: UserCreate):
    hash_pass = encrypt.hash(user.password)

    user_info = await create_user(db=db, user=user, password=hash_pass)
    user = UserRead.model_validate(user_info)
    token = await  get_access_token(str(user.id))

    return {"user": user, "access_token": token}
