from fastapi import APIRouter, Depends
from sqlmodel import Session
from app.db.session import get_session
from app.schemas.user import UserCreate, UserRead
from app.services.user_service import create_user_service
from pydantic.main import Union

from app import schemas

router = APIRouter()


@router.get("/")
async def get_users():
    return {'user': ['samuel', 'Esther', 'Solomon']}


@router.post("/user-signup", response_model=UserRead)
async def create(user_create: UserCreate, referrals: str | None = None, db: Session = Depends(get_session)):
    return create_user_service(db=db, user=user_create)
