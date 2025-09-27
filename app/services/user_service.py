from app.models import Users
from app.repositories.user_repo import create_user
from passlib.hash import pbkdf2_sha256 as encrypt
from sqlmodel import select, Session

from app.schemas.user import UserCreate, UserRead



def create_user_service(db: Session, user: UserCreate) -> UserRead:
    hash_pass = encrypt.hash(user.password)

    user_info = create_user(db=db, user=user, password=hash_pass)
    return UserRead.model_validate(user_info)
