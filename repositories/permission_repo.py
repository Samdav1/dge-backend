from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from typing import List, Optional
from app.models.permission import Permissions
from app.schemas.permission import PermissionCreate, PermissionUpdate


class PermissionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(self) -> List[Permissions]:
        stmt = select(Permissions)
        result = await self.db.exec(stmt)
        return result.all()

    async def get_by_id(self, permission_id: str) -> Optional[Permissions]:
        stmt = select(Permissions).where(Permissions.id == permission_id)
        result = await self.db.exec(stmt)
        return result.first()

    async def create(self, data: PermissionCreate) -> Permissions:
        permission = Permissions(**data.dict())
        self.db.add(permission)
        return permission

    async def update(self, permission: Permissions, data: PermissionUpdate) -> Permissions:
        for key, value in data.dict(exclude_unset=True).items():
            setattr(permission, key, value)
        return permission

    async def delete(self, permission: Permissions) -> None:
        await self.db.delete(permission)