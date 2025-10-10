from fastapi import APIRouter, Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession
from app.db.session import get_session
from app.repositories.role_repo import RoleRepository
from app.services.role_service import RoleService
from app.models.role import Roles, RoleScope
import uuid

router = APIRouter(prefix="/roles", )


@router.post("/", response_model=Roles)
async def create_role(name: str, team_user_id: uuid.UUID, scope: RoleScope, db: AsyncSession = Depends(get_session)):
    repo = RoleRepository(db)
    service = RoleService(repo)
    return await service.create_role(name, team_user_id, scope)


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
async def update_role(role_id: uuid.UUID, name: str | None = None, scope: RoleScope | None = None, db: AsyncSession = Depends(get_session)):
    repo = RoleRepository(db)
    service = RoleService(repo)
    role = await service.update_role(role_id, name, scope)
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
