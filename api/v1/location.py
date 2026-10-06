import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession
from app.db.session import get_session
from app.repositories.location_repo import LocationRepository
from app.services.location_service import LocationService
from app.schemas.location import LocationCreate, LocationUpdate, LocationRead
from app.dependencies.auth import get_current_user
from app.schemas.user import UserRead

router = APIRouter(prefix="/locations",)


@router.post("/create_user_location", response_model=LocationRead)
async def create_location(data: LocationCreate, user: UserRead = Depends(get_current_user) , db: AsyncSession = Depends(get_session)):
    repo = LocationRepository(db)
    service = LocationService(repo, user.id)
    return await service.create_location(data)


@router.get('/{location_id}', response_model=LocationRead)
async def get_location(location_id: uuid.UUID, user: UserRead = Depends(get_current_user),  db: AsyncSession = Depends(get_session)):
    repo = LocationRepository(db)
    service = LocationService(repo, user.id)
    location = await service.get_location(location_id)
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    return location


@router.get("/", response_model=list[LocationRead])
async def get_all_locations(user: UserRead = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    repo = LocationRepository(db)
    service = LocationService(repo, user.id)
    return await service.get_all_locations()


@router.get("/user/{user_id}", response_model=list[LocationRead])
async def get_user_locations(user_id: uuid.UUID, user: UserRead = Depends(get_current_user) , db: AsyncSession = Depends(get_session)):
    repo = LocationRepository(db)
    service = LocationService(repo, user.id)
    return await service.get_locations_by_user(user_id)


@router.put("/{location_id}", response_model=LocationRead)
async def update_location(location_id: uuid.UUID, data: LocationUpdate, user: UserRead = Depends(get_current_user) , db: AsyncSession = Depends(get_session)):
    repo = LocationRepository(db)
    service = LocationService(repo, user.id)
    location = await service.update_location(location_id, data)
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    return location


@router.delete("/{location_id}", response_model=dict)
async def delete_location(location_id: uuid.UUID, user: UserRead = Depends(get_current_user) , db: AsyncSession = Depends(get_session)):
    repo = LocationRepository(db)
    service = LocationService(repo, user.id)
    success = await service.delete_location(location_id)
    if not success:
        raise HTTPException(status_code=404, detail="Location not found")
    return {"message": "Location deleted successfully"}