from jose import jwt, JWTError
from typing import Any, Dict
from datetime import datetime, timedelta, timezone
import os
from dotenv import load_dotenv
from pathlib import Path

PRIVATE_KEY = Path("./../jwt_private.pem").read_text()
PUBLIC_KEY = Path("./../jwt_public.pem").read_text()

load_dotenv()

ALGORITHM = os.getenv("ALGORITHM")
TOKEN_EXPIRATION_TIME = os.getenv("ACCESS_TOKEN_EXPIRE_MINUTE")

async def get_access_token(subject: str, data: Dict[str, Any] = None, expires_delta: timedelta = None ) -> str:
    to_encode = {"sub": subject}
    if data:
        to_encode.update(data)
    expires = datetime.now(timezone.utc) +  (expires_delta or timedelta(minutes=int(TOKEN_EXPIRATION_TIME)))
    to_encode.update({"exp": expires})
    print(PRIVATE_KEY)
    return jwt.encode (to_encode, PRIVATE_KEY, algorithm=ALGORITHM)


async def decode_access_token(token: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, PUBLIC_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        raise e