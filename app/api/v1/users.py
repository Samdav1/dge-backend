from typing import Literal, Optional, Union

from fastapi import APIRouter, Depends, Response, HTTPException
from sqlmodel import Session
from starlette import status

from app.db.session import get_session
from app.dependencies.auth import get_current_user
from app.schemas.user import UserCreate, UserRead
from app.services.auth_service import issue_refresh_token, create_user_email_verification_token, verify_user_email_verification_token
from app.services.user_service import create_user_service
from pydantic.main import Union
from sqlmodel.ext.asyncio.session import AsyncSession
from app.core.security import get_access_token

from app import schemas

router = APIRouter()


@router.get("/")
async def get_users():
    return {'user': ['samuel', 'Esther', 'Solomon']}


# @router.post("/user-signup",)
# async def create(response: Response, user_create: UserCreate, referrals: str | None = None, db: AsyncSession = Depends(get_session)):
#     user = await create_user_service(db=db, user=user_create)
#     refresh_token = await issue_refresh_token(user_id=str(user["user"].id), db=db)
#
#     response.set_cookie(
#         key="refresh_token",
#         value=refresh_token,
#         httponly=True,
#         secure=True,
#         samesite= "lax",
#         max_age=7*24*60*60
#     )
#     return user

@router.post("/send_email_token")
async def send_email_verify_token(user: UserRead = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    """

    :param user:
    :param db:
    """
    from jose import JWTError
    try:
        await create_user_email_verification_token(user=user, db=db)
        return {'message': 'Email verification sent'}
    except Exception as e:
        raise HTTPException(detail=str(e), status_code=status.HTTP_400_BAD_REQUEST)


@router.put("/verify_email_token")
async def verify_email_token(token: str, db: AsyncSession = Depends(get_session)):
    """

    :param token:
    :param db:
    """

    try:
        await verify_user_email_verification_token(token=token, db=db)
        return {'message': 'Email Verification Successfully'}
    except Exception as e:
        raise HTTPException(detail=str(e), status_code=status.HTTP_400_BAD_REQUEST)


from fastapi.responses import RedirectResponse
from app.config import settings

@router.get("/verify-email")
async def verify_email_via_link(token: str, db: AsyncSession = Depends(get_session)):
    """
    GET endpoint for the email verification link.
    Verifies the token and redirects the user to the frontend email-verified page.
    """
    try:
        await verify_user_email_verification_token(token=token, db=db)
        return RedirectResponse(url=f"{settings.frontend_url}/email-verified")
    except Exception as e:
        return RedirectResponse(url=f"{settings.frontend_url}/login?error=VerificationFailed")