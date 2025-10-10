from sqlmodel.ext.asyncio.session import AsyncSession
from app.repositories.permission_repo import PermissionRepository
from app.schemas.permission import PermissionCreate, PermissionUpdate
from app.models.permission import Permissions
from typing import List, Optional
from fastapi import HTTPException, status


class PermissionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = PermissionRepository(db)

    async def list_permissions(self) -> List[Permissions]:
        return await self.repo.get_all()

    async def get_permission(self, permission_id: str) -> Permissions:
        permission = await self.repo.get_by_id(permission_id)
        if not permission:
            raise HTTPException(status_code=404, detail="Permission not found")
        return permission

    async def create_permission(self, data: PermissionCreate) -> Permissions:
        permission = await self.repo.create(data)
        await self.db.commit()
        await self.db.refresh(permission)
        return permission

    async def update_permission(self, permission_id: str, data: PermissionUpdate) -> Permissions:
        permission = await self.repo.get_by_id(permission_id)
        if not permission:
            raise HTTPException(status_code=404, detail="Permission not found")

        updated = await self.repo.update(permission, data)
        await self.db.commit()
        await self.db.refresh(updated)
        return updated

    async def delete_permission(self, permission_id: str) -> None:
        permission = await self.repo.get_by_id(permission_id)
        if not permission:
            raise HTTPException(status_code=404, detail="Permission not found")
        await self.repo.delete(permission)
        await self.db.commit()