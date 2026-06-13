from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.future import select
from app.models.role import Roles
import uuid

class RoleRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_role(self, role: Roles) -> Roles:
        self.db.add(role)
        await self.db.commit()
        await self.db.refresh(role)
        return role

    async def get_role(self, role_id: uuid.UUID) -> Roles | None:
        result = await self.db.exec(select(Roles).where(Roles.id == role_id))
        return result.scalar_one_or_none()

    async def get_roles(self) -> list[Roles]:
        result = await self.db.exec(select(Roles))
        return result.scalars().all()

    async def update_role(self, role: Roles) -> Roles:
        self.db.add(role)
        await self.db.commit()
        await self.db.refresh(role)
        return role

    async def delete_role(self, role: Roles) -> None:
        await self.db.delete(role)
        await self.db.commit()
