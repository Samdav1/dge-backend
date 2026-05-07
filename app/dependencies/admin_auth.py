from typing import Optional
from app.core.security import decode_access_token, decode_refresh_token, get_access_token
from app.repositories.user_repo import get_user_by_id
from app.schemas.super_admin import SuperAdminRead
from app.models.admin import SuperAdmin
from fastapi.security import HTTPBearer
from fastapi import Depends, Response, Request
from app.db.session import get_session
from sqlmodel.ext.asyncio.session import AsyncSession
from app.repositories.super_admin_repo import SuperAdminRepository
from fastapi import HTTPException
from jose import JWTError
from app.services.auth_service import rotate_refresh_token

security = HTTPBearer(auto_error=False)
repo = SuperAdminRepository()

async def get_current_admin(
        request: Request,
        response: Response,
        token: Optional[str] = Depends(security),
        db: AsyncSession = Depends(get_session)
):
    if not token:
        raise HTTPException(status_code=401, detail="Authentication token is missing")
    try:
        payload = await decode_access_token(token.credentials)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid admin access token payload, not valid")

        request.state.admin = user_id
        admin = await repo.get_by_id(admin_id=user_id, session=db)
        if not admin:
            raise HTTPException(status_code=404, detail="Admin not found")
        validated_admin = SuperAdminRead.model_validate(admin)
        return validated_admin
    except JWTError as e:
        refresh_token = request.cookies.get("refresh_token")
        if not refresh_token:
            raise HTTPException(status_code=401, detail="Refresh Token expired or not provided")
        try:
            payload = await decode_refresh_token(refresh_token)
            user_id = payload.get("sub")
            if not user_id:
                raise HTTPException(status_code=401, detail="Invalid refresh token payload, not valid")
            payload = await rotate_refresh_token(old_token=refresh_token, user_id=user_id, db=db)
            new_refresh_token = payload.get("token")
            admin_user = payload.get("user_id")
            request.state.admin = admin_user

            response.set_cookie(
                key="refresh_token",
                value=new_refresh_token,
                httponly=True,
                secure=True,
                samesite="lax",
                max_age=7 * 24 * 60 * 60,
            )
            admin = await repo.get_by_id(admin_id=admin_user, session=db)
            if not admin:
                raise HTTPException(status_code=404, detail="Admin not found")
            new_access_token = await get_access_token(str(admin.id))
            request.state.new_access_token = new_access_token
            refined_admin = SuperAdminRead.model_validate(admin)
            return refined_admin
        except Exception:
            raise HTTPException(status_code=401, detail="Refresh token expired or not provided. Please Login Again")

async def get_current_user_ws(token: str, db: AsyncSession):
    try:
        payload = await decode_access_token(token)
    except Exception:
        return None
        
    if not payload:
        return None
    
    user_id = payload.get("sub")
    if not user_id:
        return None
        
    # Ensure user_id is a UUID
    from uuid import UUID
    try:
        uid = UUID(user_id) if isinstance(user_id, str) else user_id
    except ValueError:
        return None

    # Try Users table
    from app.repositories.user_repo import get_user_by_id
    from app.schemas.user import UserRead
    try:
        user_info = await get_user_by_id(uid, db)
        if user_info:
            return UserRead.model_validate(user_info)
    except Exception:
        pass
        
    # Try SuperAdmin table
    from app.repositories.super_admin_repo import SuperAdminRepository
    from app.schemas.user import UserStatus
    admin_repo = SuperAdminRepository()
    admin = await admin_repo.get_by_id(session=db, admin_id=uid)
    if admin:
        return UserRead(
            id=admin.id,
            email=admin.email,
            username=admin.name,
            status=UserStatus.active,
            referral_code=None
        )
        
    return None