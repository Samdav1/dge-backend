from jose import jwt, JWTError, ExpiredSignatureError
from typing import Any, Dict
from datetime import datetime, timedelta, timezone
import os
from dotenv import load_dotenv
from pathlib import Path
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, APIKeyHeader
from fastapi import Depends, HTTPException

api_key_header = APIKeyHeader(name="token")

PRIVATE_KEY = Path("./../jwt_private.pem").read_text()
PUBLIC_KEY = Path("./../jwt_public.pem").read_text()
REFRESH_PRIVATE_KEY = Path("./../jwt_refresh_private.pem").read_text()
REFRESH_PUBLIC_KEY = Path("./../jwt_refresh_public.pem").read_text()

load_dotenv()

ALGORITHM = os.getenv("ALGORITHM")
TOKEN_EXPIRATION_TIME = os.getenv("ACCESS_TOKEN_EXPIRE_MINUTE")
LONG_TOKEN_EXPIRATION_TIME = os.getenv("REFRESH_TOKEN_EXPIRE_DAYS")
EMAIL_TOKEN_EXPIRATION_TIME = os.getenv("EMAIL_TOKEN_EXPIRE_MINUTE")


async def get_access_token(subject: str, data: Dict[str, Any] = None, expires_delta: timedelta = None) -> str:
    """

    :param subject:
    :param data:
    :param expires_delta:
    :return:
    """
    to_encode = {"sub": subject}
    if data:
        to_encode.update(data)
    expires = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=int(TOKEN_EXPIRATION_TIME)))
    to_encode.update({"exp": expires})
    return jwt.encode(to_encode, PRIVATE_KEY, algorithm=ALGORITHM)


async def decode_access_token(token: str, options: Dict[str, Any] = None) -> Dict[str, Any]:
    """

    :param token:
    :param options:
    :return:
    """
    try:
        payload = jwt.decode(token, PUBLIC_KEY, algorithms=[ALGORITHM], options=options)
        return payload
    except JWTError as e:
        raise e


async def get_refresh_token(subject: str, data: Dict[str, Any] = None, expires_delta: timedelta = None) -> str:
    """

    :param subject:
    :param data:
    :param expires_delta:
    :return:
    """
    to_encode = {"sub": subject}
    if data:
        to_encode.update(data)
    expires = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=int(LONG_TOKEN_EXPIRATION_TIME)))
    to_encode.update({"exp": expires})
    return jwt.encode(to_encode, REFRESH_PRIVATE_KEY, algorithm=ALGORITHM)


async def decode_refresh_token(token: str, options: Dict[str, Any] = None) -> Dict[str, Any]:
    """

    :param token:
    :param options:
    :return:
    """
    try:
        payload = jwt.decode(token, REFRESH_PUBLIC_KEY, algorithms=[ALGORITHM], options=options)
        return payload
    except JWTError as e:
        raise e


async def create_email_token(subject: str, data: Dict[str, Any] = None, expires_delta: timedelta = None) -> str:
    """

    :param subject:
    :param data:
    :param expires_delta:
    :return:
    """
    to_encode = {"sub": subject}
    if data:
        to_encode.update(data)
    expires = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=int(EMAIL_TOKEN_EXPIRATION_TIME)))
    to_encode.update({"exp": expires})
    return jwt.encode(to_encode, PRIVATE_KEY, algorithm=ALGORITHM)


async def decode_email_token(token: str, options: Dict[str, Any] = None) -> Dict[str, Any]:
    """

    :param token:
    :param options:
    :return:
    """
    try:
        payload = jwt.decode(token, PUBLIC_KEY, algorithms=[ALGORITHM], options=options)
        return payload
    except JWTError as e:
        raise e

# async def jwt_decorator(func):
#     async def wrapper(*args, **kwargs):
#         if func(Depends(api_key_header)):
#             payload = await decode_access_token(Depends(api_key_header), options={"verify_exp": False})
#             if payload:
#                 userid = payload["sub"]
#                 new_token = await get_long_token(userid)
#                 return new_token
#             else:
#                 raise HTTPException(status_code=401, detail="Unauthorized")
#         else:
#             raise HTTPException(status_code=401, detail="Unauthorized")
#     return wrapper
