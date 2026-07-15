from jose import jwt, JWTError, ExpiredSignatureError
from typing import Any, Dict
from datetime import datetime, timedelta, timezone
import os
from dotenv import load_dotenv
from pathlib import Path
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, APIKeyHeader
from fastapi import Depends, HTTPException

api_key_header = APIKeyHeader(name="token")

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent

import logging

logger = logging.getLogger(__name__)

def _load_key_from_env_or_file(env_var: str, filename: str, fallback_env_var: str = None, fallback_filename: str = None) -> str:
    try:
        # 1. Try primary env var
        value = os.getenv(env_var)
        if not value and fallback_env_var:
            # 2. Try fallback env var
            value = os.getenv(fallback_env_var)
            
        if value:
            # Standardize newlines (replace literal '\n' sequences with real newlines)
            return value.replace("\\n", "\n").strip('"\'')
            
        # 3. Try primary file path
        path = BASE_DIR / filename
        if path.exists():
            return path.read_text()
            
        # 4. Try fallback file path
        if fallback_filename:
            fallback_path = BASE_DIR / fallback_filename
            if fallback_path.exists():
                return fallback_path.read_text()
                
        raise FileNotFoundError(f"Key not found in env ({env_var}) or file ({filename}).")
    except Exception as e:
        logger.warning(f"⚠️ Security key warning: {e}. Please ensure env var {env_var} is set in production.")
        return ""

PRIVATE_KEY = _load_key_from_env_or_file("JWT_PRIVATE_KEY", "jwt_private.pem")
PUBLIC_KEY = _load_key_from_env_or_file("JWT_PUBLIC_KEY", "jwt_public.pem")
REFRESH_PRIVATE_KEY = _load_key_from_env_or_file("JWT_REFRESH_PRIVATE_KEY", "jwt_refresh_private.pem", fallback_env_var="JWT_PRIVATE_KEY", fallback_filename="jwt_private.pem")
REFRESH_PUBLIC_KEY = _load_key_from_env_or_file("JWT_REFRESH_PUBLIC_KEY", "jwt_refresh_public.pem", fallback_env_var="JWT_PUBLIC_KEY", fallback_filename="jwt_public.pem")


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
    expires = datetime.now(timezone.utc) + (expires_delta or timedelta(days=int(LONG_TOKEN_EXPIRATION_TIME)))
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
