from fastapi import HTTPException
from starlette import status
from app.schemas.user import UserLogin, UserRead, UserToken
from passlib.hash import pbkdf2_sha256 as decrypt
from app.repositories.user_repo import get_user, get_user_token


async def login(user_info: UserLogin, db):
    user_detail = get_user(user_info, db)
    print(f"Hash Pass: {user_detail.password}, Raw Pass: {user_info.password} ")
    if not user_detail:
        return False
    elif not decrypt.verify(user_info.password, user_detail.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect password")
    else:
     return UserRead.model_validate(user_detail)

async def token_login(user_info: UserToken, db):
    user_detail = get_user_token(user_info, db)
    print(f"Hash Pass: {user_detail.password}, Raw Pass: {user_info.password} ")
    if not user_detail:
        return False
    elif not decrypt.verify(user_info.password, user_detail.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect password")
    else:
     return UserRead.model_validate(user_detail)