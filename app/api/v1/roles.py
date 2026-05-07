from fastapi import APIRouter, Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession
from app.db.session import get_session
from app.repositories.role_repo import RoleRepository
from app.services.role_service import RoleService
from app.models.role import Roles, RoleScope
import uuid

router = APIRouter(prefix="", )

from pydantic import BaseModel
from typing import Optional
from app.models.role import RoleStatus

class RoleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    scope: RoleScope = RoleScope.global_scope
    status: RoleStatus = RoleStatus.ACTIVE

class RoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    scope: Optional[RoleScope] = None
    status: Optional[RoleStatus] = None

@router.post("/", response_model=Roles)
async def create_role(role_data: RoleCreate, db: AsyncSession = Depends(get_session)):
    repo = RoleRepository(db)
    service = RoleService(repo)
    return await service.create_role(role_data.name, role_data.description, role_data.scope, role_data.status)


@router.get("/{role_id}", response_model=Roles)
async def get_role(role_id: uuid.UUID, db: AsyncSession = Depends(get_session)):
    repo = RoleRepository(db)
    service = RoleService(repo)
    role = await service.get_role(role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    return role


@router.get("/", response_model=list[Roles])
async def get_roles(db: AsyncSession = Depends(get_session)):
    repo = RoleRepository(db)
    service = RoleService(repo)
    return await service.get_roles()


@router.put("/{role_id}", response_model=Roles)
async def update_role(role_id: uuid.UUID, role_data: RoleUpdate, db: AsyncSession = Depends(get_session)):
    repo = RoleRepository(db)
    service = RoleService(repo)
    role = await service.update_role(role_id, role_data.name, role_data.description, role_data.scope, role_data.status)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    return role


@router.delete("/{role_id}", response_model=dict)
async def delete_role(role_id: uuid.UUID, db: AsyncSession = Depends(get_session)):
    repo = RoleRepository(db)
    service = RoleService(repo)
    success = await service.delete_role(role_id)
    if not success:
        raise HTTPException(status_code=404, detail="Role not found")
    return {"message": "Role deleted successfully"}
