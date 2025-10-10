from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field
from app.models.permission import PermissionEffect


class PermissionCreate(BaseModel):
    role_id: UUID
    resource: str
    action: str
    team_user_id: UUID
    effect: PermissionEffect = PermissionEffect.allow
    conditions: Dict[str, Any] = Field(default_factory=dict)


class PermissionUpdate(BaseModel):
    resource: Optional[str] = None
    action: Optional[str] = None
    effect: Optional[PermissionEffect] = None
    conditions: Optional[Dict[str, Any]] = None


class PermissionRead(BaseModel):
    id: UUID
    role_id: UUID
    resource: str
    action: str
    team_user_id: UUID
    effect: PermissionEffect
    conditions: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
