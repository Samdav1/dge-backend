# app/schemas/superadmin.py
from __future__ import annotations
from typing import Optional
from uuid import UUID
from datetime import datetime
from fastapi import Form, UploadFile
from pydantic import BaseModel, EmailStr, Field, constr
from app.models.admin import AdminRank, AdminStatus

# basic validators
NameStr = constr(min_length=2, max_length=150)
PasswordStr = constr(min_length=8)


class SuperAdminBase(BaseModel):
    name: NameStr
    email: EmailStr
    phone_number: Optional[str] = None
    rank: Optional[AdminRank] = AdminRank.Major
    is_active: Optional[bool] = True
    email_verified: Optional[bool] = False
    phone_verified: Optional[bool] = False
    mfa_enabled: Optional[bool] = False

    class Config:
        from_attributes = True


# --- FORM schema (multipart data) ---
class SuperAdminCreateForm:
    def __init__(
            self,
            name: str = Form(...),
            email: EmailStr = Form(...),
            password: str = Form(...),
            phone_number: Optional[str] = Form(None),
            rank: Optional[AdminRank] = Form(AdminRank.Major),
            avatar: UploadFile = None,
    ):
        self.name = name
        self.email = email
        self.password = password
        self.phone_number = phone_number
        self.rank = rank
        self.avatar = avatar


class SuperAdminRead(BaseModel):
    id: UUID
    name: str
    email: EmailStr
    phone_number: Optional[str] = None
    rank: AdminRank
    status: AdminStatus
    is_active: bool
    email_verified: bool
    phone_verified: bool
    avatar: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class SuperAdminLoginRead(BaseModel):
    name: str
    email: EmailStr
    phone_number: Optional[str] = None
    rank: AdminRank
    status: AdminStatus
    is_active: bool
    email_verified: bool
    phone_verified: bool
    avatar: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class AdminLogin(BaseModel):
    username: str
    password: str

    class Config:
        from_attributes = True
