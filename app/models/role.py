import uuid
from datetime import datetime, timezone
from enum import Enum
from sqlmodel import SQLModel, Field, Relationship


class RoleScope(str, Enum):
    team = "team"
    global_scope = "global"   # use "global_scope" instead of "global" (since `global` is a reserved Python keyword)


class Roles(SQLModel, table=True):
    __tablename__ = "roles"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    name: str = Field(nullable=False, unique=True, index=True)
    team_user_id: uuid.UUID = Field(foreign_key="teamusers.id", nullable=False, index=True)
    scope: RoleScope = Field(default=RoleScope.team, nullable=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    team_user:'TeamUsers' = Relationship(back_populates="role")

