import uuid
from datetime import date, datetime
from typing import Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field

if TYPE_CHECKING:
    from .user import UserRead


class ProfileBase(SQLModel):
    first_name: str
    last_name: str
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    phone: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: str
    bio: Optional[str] = None
    avatar_url: Optional[str] = None


class ProfileCreate(ProfileBase):
    user_id: uuid.UUID
    team_id: Optional[uuid.UUID] = None


class ProfileUpdate(SQLModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    phone: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    team_id: Optional[uuid.UUID] = None


class ProfileRead(ProfileBase):
    id: uuid.UUID
    user_id: uuid.UUID
    team_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime


class ProfileReadWithUser(ProfileRead):
    user: Optional["UserRead"] = None


# class ProfileReadWithTeam(ProfileRead):
#     team: Optional["TeamUsersRead"] = None

# ProfileReadWithTeam.model_rebuild()

from .user import UserRead
ProfileReadWithUser.model_rebuild()
