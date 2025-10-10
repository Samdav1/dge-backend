from app.repositories.team_repo import TeamRepository
from app.schemas.team import TeamCreate, TeamUpdate, TeamUserCreate, TeamUserUpdate, TeamMembershipCreate
from passlib.hash import pbkdf2_sha256 as encrypt


class TeamService:
    def __init__(self, repo: TeamRepository):
        self.repo = repo

    # TEAM
    async def create_team(self, payload: TeamCreate):
        return await self.repo.create_team(payload)

    async def get_team(self, team_id):
        return await self.repo.get_team(team_id)

    async def get_teams(self):
        return await self.repo.get_teams()

    async def update_team(self, team_id, payload: TeamUpdate):
        return await self.repo.update_team(team_id, payload)

    async def delete_team(self, team_id):
        return await self.repo.delete_team(team_id)


    # TEAM USERS
    async def create_team_user(self, payload: TeamUserCreate):
        hash_password = encrypt.encrypt(payload.password)
        new_team_schemas = TeamUserCreate(
                full_name=payload.full_name,
                email=payload.email,
                password=hash_password,
                phone=payload.phone,
        )
        return await self.repo.create_team_user(new_team_schemas)

    async def get_team_user(self, user_id):
        return await self.repo.get_team_user(user_id)

    async def get_team_users(self):
        return await self.repo.get_team_users()

    async def update_team_user(self, user_id, payload: TeamUserUpdate):
        return await self.repo.update_team_user(user_id, payload)

    async def delete_team_user(self, user_id):
        return await self.repo.delete_team_user(user_id)


    # MEMBERSHIP
    async def add_user_to_team(self, payload: TeamMembershipCreate):
        return await self.repo.add_user_to_team(payload)

    async def remove_user_from_team(self, team_id, user_id):
        return await self.repo.remove_user_from_team(team_id, user_id)