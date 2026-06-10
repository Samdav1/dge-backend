# app/repositories/team_repo.py
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.exc import NoResultFound
from uuid import UUID

from app.models.team import Teams, TeamUsers, TeamMembership
from app.schemas.team import TeamCreate, TeamUpdate, TeamUserCreate, TeamUserUpdate, TeamMembershipCreate


class TeamRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ---------------- TEAM ----------------
    async def create_team(self, payload: TeamCreate) -> Teams:
        team = Teams(**payload.dict())
        self.db.add(team)
        await self.db.commit()
        await self.db.refresh(team)
        return team

    async def get_team(self, team_id: UUID) -> Teams | None:
        stmt = select(Teams).where(Teams.id == team_id)
        result = await self.db.exec(stmt)
        return result.first()

    async def get_teams(self) -> list[Teams]:
        stmt = select(Teams).order_by(Teams.created_at.desc())
        result = await self.db.exec(stmt)
        return result.all()

    async def update_team(self, team_id: UUID, payload: TeamUpdate) -> Teams:
        team = await self.get_team(team_id)
        if not team:
            raise NoResultFound("Team not found")
        for k, v in payload.dict(exclude_unset=True).items():
            setattr(team, k, v)
        self.db.add(team)
        await self.db.commit()
        await self.db.refresh(team)
        return team

    async def delete_team(self, team_id: UUID):
        team = await self.get_team(team_id)
        if not team:
            raise NoResultFound("Team not found")
        await self.db.delete(team)
        await self.db.commit()
        return {"deleted": True, "team_id": str(team_id)}



    # ---------------- TEAM USERS ----------------
    async def create_team_user(self, payload: TeamUserCreate) -> TeamUsers:
        user = TeamUsers(
            email=payload.email,
            password_hash=payload.password,
            full_name=payload.full_name,
            phone=payload.phone,
            is_superuser=payload.is_superuser,
            status=payload.status,
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def get_team_user(self, user_id: UUID) -> TeamUsers | None:
        stmt = select(TeamUsers).where(TeamUsers.id == user_id)
        result = await self.db.exec(stmt)
        return result.first()

    async def get_team_user_by_email(self, email: str) -> TeamUsers | None:
        stmt = select(TeamUsers).where(TeamUsers.email == email)
        result = await self.db.exec(stmt)
        return result.first()

    async def get_team_users(self) -> list[TeamUsers]:
        stmt = select(TeamUsers).order_by(TeamUsers.created_at.desc())
        result = await self.db.exec(stmt)
        return result.all()

    async def update_team_user(self, user_id: UUID, payload: TeamUserUpdate) -> TeamUsers:
        user = await self.get_team_user(user_id)
        if not user:
            raise NoResultFound("User not found")
        for k, v in payload.dict(exclude_unset=True).items():
            setattr(user, k, v)
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def delete_team_user(self, user_id: UUID):
        user = await self.get_team_user(user_id)
        if not user:
            raise NoResultFound("User not found")
        await self.db.delete(user)
        await self.db.commit()
        return {"deleted": True, "user_id": str(user_id)}


    # ---------------- MEMBERSHIP ----------------
    async def add_user_to_team(self, payload: TeamMembershipCreate) -> TeamMembership:
        membership = TeamMembership(**payload.dict())
        self.db.add(membership)
        await self.db.commit()
        await self.db.refresh(membership)
        return membership

    async def remove_user_from_team(self, team_id: UUID, user_id: UUID):
        stmt = select(TeamMembership).where(
            TeamMembership.team_id == team_id,
            TeamMembership.user_id == user_id
        )
        result = await self.db.exec(stmt)
        membership = result.first()
        if not membership:
            raise NoResultFound("Membership not found")
        await self.db.delete(membership)
        await self.db.commit()
        return {"deleted": True, "team_id": str(team_id), "user_id": str(user_id)}