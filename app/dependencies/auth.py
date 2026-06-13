from fastapi import Depends, HTTPException, Request, Response
from fastapi.security import HTTPBearer
from sqlmodel.ext.asyncio.session import AsyncSession
from jose import JWTError, ExpiredSignatureError
from app.core.security import get_access_token, decode_access_token, decode_refresh_token
from app.db.session import get_session
from app.models.user import Users
from app.repositories.user_repo import get_user_by_id
from app.services.auth_service import rotate_refresh_token
from app.schemas.user import UserRead

from datetime import datetime, timezone, timedelta
from app.repositories.refresh_token_repo import get_by_token

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
            print(f"DEBUG AUTH: No sub in payload")
            raise HTTPException(status_code=401, detail="Invalid access token payload, not valid")

        request.state.user_id = user_id
        
        # Ensure user_id is a UUID if it's a string
        from uuid import UUID
        try:
            uid = UUID(user_id) if isinstance(user_id, str) else user_id
        except ValueError:
            print(f"DEBUG AUTH: Invalid UUID format: {user_id}")
            raise HTTPException(status_code=401, detail="Invalid user ID format")

        # Try finding in Users table
        try:
            user = await get_user_by_id(uid, db)
            if user:
                print(f"DEBUG AUTH: Found user in Users table: {uid}")
                return UserRead.model_validate(user)
        except Exception as e:
            print(f"DEBUG AUTH: Error searching Users table: {e}")
        
        # Try finding in SuperAdmin table if not in Users
        from app.repositories.super_admin_repo import SuperAdminRepository
        from app.schemas.user import UserStatus
        admin_repo = SuperAdminRepository()
        admin = await admin_repo.get_by_id(session=db, admin_id=uid)
        if admin:
            print(f"DEBUG AUTH: Found user in SuperAdmin table: {uid}")
            return UserRead(
                id=admin.id,
                email=admin.email,
                username=admin.name,
                status=UserStatus.active,
                referral_code=None,
                is_admin=True
            )

        print(f"DEBUG AUTH: User or Admin not found for ID: {uid}")
        raise HTTPException(status_code=401, detail="User or Admin not found")

    except JWTError as e:
        print(f"DEBUG AUTH: Access token expired/invalid: {str(e)}")
        refresh_token = request.cookies.get("refresh_token")
        if not refresh_token:
            raise HTTPException(status_code=401, detail="Session expired, please login again")

        try:
            # Check revocation status with grace period before rotating
            db_token = await get_by_token(db, refresh_token)
            if not db_token or db_token.expires_at < datetime.now(timezone.utc):
                raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

            if db_token.revoked:
                # 30-second grace period for recently rotated tokens
                grace_period = timedelta(seconds=30)
                if not db_token.revoked_at or (datetime.now(timezone.utc) - db_token.revoked_at) > grace_period:
                    raise HTTPException(status_code=401, detail="Refresh token has been revoked")

            refresh_payload = await decode_refresh_token(refresh_token)
            user_id_from_refresh = refresh_payload.get("sub")
            
            # Rotate token
            rotated_token = await rotate_refresh_token(old_token=refresh_token, db=db, user_id=user_id_from_refresh)
            new_refresh_token = rotated_token.token
            user_id = rotated_token.user_id
            
            from uuid import UUID
            uid = UUID(user_id) if isinstance(user_id, str) else user_id
            
            # Find User or Admin
            user = None
            try:
                user = await get_user_by_id(uid, db)
            except Exception:
                pass
                
            if not user:
                from app.repositories.super_admin_repo import SuperAdminRepository
                from app.schemas.user import UserStatus
                admin_repo = SuperAdminRepository()
                admin = await admin_repo.get_by_id(session=db, admin_id=uid)
                if admin:
                    user = UserRead(
                        id=admin.id, email=admin.email, username=admin.name,
                        status=UserStatus.active, referral_code=None, is_admin=True
                    )

            if not user:
                raise HTTPException(status_code=401, detail="User not found after refresh")

            # Update cookies and state
            response.set_cookie(
                key="refresh_token",
                value=new_refresh_token,
                httponly=True,
                secure=True,
                samesite="lax",
                max_age=7 * 24 * 60 * 60,
            )

            new_access_token = await get_access_token(str(uid))
            request.state.new_access_token = new_access_token

            return user if isinstance(user, UserRead) else UserRead.model_validate(user)

        except Exception as exc:
            print(f"DEBUG AUTH: Auto-refresh failed: {str(exc)}")
            raise HTTPException(status_code=401, detail="Session expired, please login again")