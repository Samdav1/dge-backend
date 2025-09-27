from fastapi import APIRouter
from fastapi.security import OAuth2PasswordRequestForm
from app.schemas.user import *
from sqlmodel import SQLModel, Session
from fastapi import Depends
from app.db.session import get_session
from app.services.auth_service import login, token_login
from app.core.security import get_access_token
import asyncio
from pydantic import json


router = APIRouter()

@router.post("/login")
async def user_login(user_ifo: UserLogin, db: Session=Depends(get_session) ):
    return await login(user_ifo, db)


@router.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_session)):
    user_ifo = UserToken.model_validate({
        "username": form_data.username,
        "password": form_data.password
    })
    data = await token_login(user_ifo, db)
    id_value = str(data.id)
    token = await get_access_token(subject=id_value)
    return {"access_token": token, "token_type": "bearer"}




