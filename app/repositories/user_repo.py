from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError

from app.schemas.user import *
from sqlmodel import Session, select
from app.models.user import Users




def create_user(db: Session, user: UserCreate, password: str):
    user = Users(username=user.username, email=user.email, password=password)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def get_user(user_info: UserLogin, db):
    user = select(Users).where(Users.email == user_info.email)
    result = db.execute(user).scalar()
    if result is None:
        raise HTTPException(status_code=404, detail="User not found")
    else:
        return result

def get_user_token(user_info: UserToken, db):
    user = select(Users).where(Users.username == user_info.username)
    result = db.execute(user).scalar()
    if result is None:
        raise HTTPException(status_code=404, detail="User not found")
    else:
        return result