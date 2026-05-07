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
        print(f"DEBUG AUTH: JWTError: {str(e)}")
        refresh_token = request.cookies.get("refresh_token")
        if not refresh_token:
            raise HTTPException(status_code=401, detail="Refresh Token expired or not provided")

        try:
            refresh_payload = await decode_refresh_token(refresh_token)
            user_id_from_refresh = refresh_payload.get("sub")
            
            # Rotate token
            payload = await rotate_refresh_token(old_token=refresh_token, db=db, user_id=user_id_from_refresh)
            new_refresh_token = payload.get("token")
            user_id = payload.get("user_id")
            
            # Fallback check for admin if rotate_refresh_token or user lookup fails
            from uuid import UUID
            uid = UUID(user_id) if isinstance(user_id, str) else user_id
            
            # Try finding in Users
            user = None
            try:
                user = await get_user_by_id(uid, db)
            except HTTPException:
                pass
                
            if not user:
                # Try finding in SuperAdmin
                from app.repositories.super_admin_repo import SuperAdminRepository
                from app.schemas.user import UserStatus
                admin_repo = SuperAdminRepository()
                admin = await admin_repo.get_by_id(session=db, admin_id=uid)
                if admin:
                    user = UserRead(
                        id=admin.id,
                        email=admin.email,
                        username=admin.name,
                        status=UserStatus.active,
                        referral_code=None,
                        is_admin=True
                    )

            if not user:
                raise HTTPException(status_code=401, detail="User or Admin not found during refresh")

            # Set new refresh token cookie
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

        except Exception as e:
            print(f"DEBUG AUTH: Refresh failed: {str(e)}")
            raise HTTPException(status_code=401, detail="Refresh expired or failed")

        except Exception:
            raise HTTPException(status_code=401, detail="Refresh expired, please login again")