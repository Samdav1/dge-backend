import uuid
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import Column, DateTime
from sqlmodel import SQLModel, Field, Relationship


class RoleScope(str, Enum):
    team = "team"
    global_scope = "global"   # use "global_scope" instead of "global" (since `global` is a reserved Python keyword)


class RoleStatus(str, Enum):
    ACTIVE = "ACTIVE"
    DEACTIVATED = "DEACTIVATED"

class Roles(SQLModel, table=True):
    __tablename__ = "roles"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    name: str = Field(nullable=False, unique=True, index=True)
    description: str | None = Field(default=None)
    scope: RoleScope = Field(default=RoleScope.team, nullable=False)
    status: RoleStatus = Field(default=RoleStatus.ACTIVE, nullable=False)
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False),
        default_factory=lambda: datetime.now(timezone.utc),
    )
    updated_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False),
        default_factory=lambda: datetime.now(timezone.utc),
    )
    
    # One-to-Many relationship: One Role can be assigned to multiple TeamUsers
    team_users: list['TeamUsers'] = Relationship(back_populates="role")

