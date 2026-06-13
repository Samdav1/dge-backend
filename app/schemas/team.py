
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from app.models.team import TeamType
from app.models.user import UserStatus

class TeamBase(BaseModel):
    name: str
    description: Optional[str] = None
    team_type: TeamType = TeamType.customer_service


class TeamCreate(TeamBase):
    pass


class TeamRead(TeamBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TeamUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    team_type: Optional[TeamType] = None


class TeamUserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    phone: Optional[str] = None
    is_superuser: bool = False
    status: UserStatus = UserStatus.active


class TeamUserCreate(TeamUserBase):
    password: str


class TeamUserRead(TeamUserBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class TeamUserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    is_superuser: Optional[bool] = None
    status: Optional[UserStatus] = None

class TeamMembershipBase(BaseModel):
    team_id: UUID
    user_id: UUID


class TeamMembershipCreate(TeamMembershipBase):
    pass


class TeamMembershipRead(TeamMembershipBase):
    joined_at: datetime

    class Config:
        from_attributes = True