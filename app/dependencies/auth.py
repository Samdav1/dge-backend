from fastapi import Depends, HTTPException, Request, Response
from fastapi.security import HTTPBearer
from sqlmodel.ext.asyncio.session import AsyncSession
from jose import JWTError, ExpiredSignatureError
from app.core.security import get_access_token, decode_access_token, decode_refresh_token
from app.db.session import get_session
from app.models.user import Users
from app.repositories.user_repo import get_user_by_id
from app.services.auth_service import rotate_refresh_token

security = HTTPBearer()

async def get_current_user(
    request: Request,
    response: Response,
    token: str = Depends(security),
    db: AsyncSession = Depends(get_session),
):
    try:
        payload = await decode_access_token(token.credentials)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid access token payload, not valid")

        request.state.user_id = user_id
        user = await get_user_by_id(user_id, db)
        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        return user

    except JWTError:
        refresh_token = request.cookies.get("refresh_token")
        if not refresh_token:
            raise HTTPException(status_code=401, detail="Refresh Token expired or not provided, please login again")

        try:
            refresh_payload = await decode_refresh_token(refresh_token)
            user_from_refresh_token = refresh_payload.get("sub")
            payload = await rotate_refresh_token(old_token=refresh_token, db=db, user_id=user_from_refresh_token)
            new_refresh_token = payload.get("token")
            user_id = payload.get("user_id")
            request.state.user_id = user_id

            response.set_cookie(
                key="refresh_token",
                value=new_refresh_token,
                httponly=True,
                secure=True,
                samesite="lax",
                max_age=7 * 24 * 60 * 60,
            )

            user = await get_user_by_id(user_id, db)
            if not user:
                raise HTTPException(status_code=401, detail="User not found")

            new_access_token = await get_access_token(str(user.id))
            request.state.new_access_token = new_access_token

            return user

        except Exception:
            raise HTTPException(status_code=401, detail="Refresh expired, please login again")