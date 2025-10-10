from app.repositories.role_repo import RoleRepository
from app.models.role import Roles, RoleScope
import uuid

class RoleService:
    def __init__(self, repo: RoleRepository):
        self.repo = repo

    async def create_role(self, name: str, team_user_id: uuid.UUID, scope: RoleScope) -> Roles:
        role = Roles(name=name, team_user_id=team_user_id, scope=scope)
        return await self.repo.create_role(role)

    async def get_role(self, role_id: uuid.UUID) -> Roles | None:
        return await self.repo.get_role(role_id)

    async def get_roles(self) -> list[Roles]:
        return await self.repo.get_roles()

    async def update_role(self, role_id: uuid.UUID, name: str | None = None, scope: RoleScope | None = None) -> Roles | None:
        role = await self.repo.get_role(role_id)
        if not role:
            return None
        if name:
            role.name = name
        if scope:
            role.scope = scope
        return await self.repo.update_role(role)

    async def delete_role(self, role_id: uuid.UUID) -> bool:
        role = await self.repo.get_role(role_id)
        if not role:
            return False
        await self.repo.delete_role(role)
        return True