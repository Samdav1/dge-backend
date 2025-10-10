from fastapi import APIRouter, Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.exc import NoResultFound
from typing import List
from uuid import UUID
from app.db.session import get_session
from app.repositories.team_repo import TeamRepository
from app.services.team_service import TeamService
from app.schemas.team import (
    TeamCreate, TeamRead, TeamUpdate,
    TeamUserCreate, TeamUserRead, TeamUserUpdate,
    TeamMembershipCreate, TeamMembershipRead
)

router = APIRouter(prefix="/teams", )


# ---------------- TEAM ----------------
@router.post("/", response_model=TeamRead)
async def create_team(payload: TeamCreate, db: AsyncSession = Depends(get_session)):
    service = TeamService(TeamRepository(db))
    return await service.create_team(payload)


@router.get("/{team_id}", response_model=TeamRead)
async def get_team(team_id: UUID, db: AsyncSession = Depends(get_session)):
    service = TeamService(TeamRepository(db))
    team = await service.get_team(team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return team


@router.get("/", response_model=List[TeamRead])
async def get_teams(db: AsyncSession = Depends(get_session)):
    service = TeamService(TeamRepository(db))
    return await service.get_teams()


@router.put("/{team_id}", response_model=TeamRead)
async def update_team(team_id: UUID, payload: TeamUpdate, db: AsyncSession = Depends(get_session)):
    service = TeamService(TeamRepository(db))
    try:
        return await service.update_team(team_id, payload)
    except NoResultFound:
        raise HTTPException(status_code=404, detail="Team not found")


@router.delete("/{team_id}")
async def delete_team(team_id: UUID, db: AsyncSession = Depends(get_session)):
    service = TeamService(TeamRepository(db))
    try:
        return await service.delete_team(team_id)
    except NoResultFound:
        raise HTTPException(status_code=404, detail="Team not found")


# ---------------- TEAM USERS ----------------
@router.post("/users", response_model=TeamUserRead)
async def create_team_user(payload: TeamUserCreate, db: AsyncSession = Depends(get_session)):
    service = TeamService(TeamRepository(db))
    return await service.create_team_user(payload)


@router.get("/users/{user_id}", response_model=TeamUserRead)
async def get_team_user(user_id: UUID, db: AsyncSession = Depends(get_session)):
    service = TeamService(TeamRepository(db))
    user = await service.get_team_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/users", response_model=List[TeamUserRead])
async def get_team_users(db: AsyncSession = Depends(get_session)):
    service = TeamService(TeamRepository(db))
    return await service.get_team_users()


@router.put("/users/{user_id}", response_model=TeamUserRead)
async def update_team_user(user_id: UUID, payload: TeamUserUpdate, db: AsyncSession = Depends(get_session)):
    service = TeamService(TeamRepository(db))
    try:
        return await service.update_team_user(user_id, payload)
    except NoResultFound:
        raise HTTPException(status_code=404, detail="User not found")


@router.delete("/users/{user_id}")
async def delete_team_user(user_id: UUID, db: AsyncSession = Depends(get_session)):
    service = TeamService(TeamRepository(db))
    try:
        return await service.delete_team_user(user_id)
    except NoResultFound:
        raise HTTPException(status_code=404, detail="User not found")


# ---------------- MEMBERSHIP ----------------
@router.post("/membership", response_model=TeamMembershipRead)
async def add_user_to_team(payload: TeamMembershipCreate, db: AsyncSession = Depends(get_session)):
    service = TeamService(TeamRepository(db))
    return await service.add_user_to_team(payload)


@router.delete("/membership/{team_id}/{user_id}")
async def remove_user_from_team(team_id: UUID, user_id: UUID, db: AsyncSession = Depends(get_session)):
    service = TeamService(TeamRepository(db))
    try:
        return await service.remove_user_from_team(team_id, user_id)
    except NoResultFound:
        raise HTTPException(status_code=404, detail="Membership not found")