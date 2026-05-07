from app.repositories.role_repo import RoleRepository
from app.models.role import Roles, RoleScope
import uuid

class RoleService:
    def __init__(self, repo: RoleRepository):
        self.repo = repo

    async def create_role(self, name: str, description: str | None, scope: RoleScope, status: str) -> Roles:
        role = Roles(name=name, description=description, scope=scope, status=status)
        return await self.repo.create_role(role)

    async def get_role(self, role_id: uuid.UUID) -> Roles | None:
        return await self.repo.get_role(role_id)

    async def get_roles(self) -> list[Roles]:
        return await self.repo.get_roles()

    async def update_role(self, role_id: uuid.UUID, name: str | None = None, description: str | None = None, scope: RoleScope | None = None, status: str | None = None) -> Roles | None:
        role = await self.repo.get_role(role_id)
        if not role:
            return None
        if name is not None:
            role.name = name
        if description is not None:
            role.description = description
        if scope is not None:
            role.scope = scope
        if status is not None:
            role.status = status
        return await self.repo.update_role(role)

    async def delete_role(self, role_id: uuid.UUID) -> bool:
        role = await self.repo.get_role(role_id)
        if not role:
            return False
        await self.repo.delete_role(role)
        return True