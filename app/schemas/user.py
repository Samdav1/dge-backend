from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional, TYPE_CHECKING
from enum import Enum
import uuid

if TYPE_CHECKING:
    from .profile import *


class UserStatus(str, Enum):
    active = "active"
    deleted = "deleted"
    banned = "banned"
    approved = "approved"


class UserBase(BaseModel):
    username: str
    email: EmailStr

    model_config = ConfigDict(from_attributes=True)
class UserLogin(BaseModel):
    username: str
    password: str

    model_config = ConfigDict(from_attributes=True)
class UserCreate(UserBase):
    password: str
    referral_code: Optional[str]
    google_auth: bool = False

    model_config = ConfigDict(from_attributes=True)
class UserRead(UserBase):
    id: uuid.UUID
    status: UserStatus
    referral_code: Optional[str]
    is_admin: bool = False
    email_verified: bool = False
    google_auth: bool = False

    model_config = ConfigDict(from_attributes=True)
class UserReadWithProfile(UserRead):
    profile: Optional["ProfileRead"]

class UserToken(BaseModel):
    username: str
    password: str

from .profile import *
UserReadWithProfile.model_rebuild()

class UserGoogleCreate(UserBase):
    referral_code: Optional[str]
    google_auth: bool = True

    model_config = ConfigDict(from_attributes=True)
