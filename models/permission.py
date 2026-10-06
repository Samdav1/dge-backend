import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Any

from sqlalchemy import DateTime
from sqlmodel import SQLModel, Field, Relationship, Column, JSON


class PermissionEffect(str, Enum):
    allow = "allow"
    deny = "deny"


class Permissions(SQLModel, table=True):
    __tablename__ = "permissions"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    role_id: uuid.UUID = Field(foreign_key="roles.id", nullable=False, index=True)
    resource: str = Field(nullable=False, index=True)
    action: str = Field(nullable=False, index=True)
    team_user_id: uuid.UUID = Field(foreign_key="teamusers.id", nullable=False, index=True)
    effect: PermissionEffect = Field(
        default=PermissionEffect.allow, nullable=False
    )
    conditions: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False)
    )
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False),
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False),
        default_factory=lambda: datetime.now(timezone.utc)
    )

    team_user:'TeamUsers' = Relationship(back_populates="permissions")