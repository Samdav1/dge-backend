import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession
from app.db.session import get_session
from app.dependencies.auth import get_current_user
from app.schemas.driving import DriverCreate, DriverRead, DriverUpdate, RideCreate, RideRead, RideComplete, \
    DriverNearbyResponse, LocationUpdate
from app.schemas.user import UserRead
from app.services.driving_service import DriverService, RideService, LocationService

router = APIRouter(prefix="/drivers", tags=["Drivers"])

def get_driver_service(db: AsyncSession = Depends(get_session)):
    """

    :param db:
    :return:
    """
    return DriverService(db)


@router.post("/", response_model=DriverRead, status_code=status.HTTP_201_CREATED)
async def create_driver_profile(
        payload: DriverCreate,
        current_user: UserRead = Depends(get_current_user),
        service: DriverService = Depends(get_driver_service),
):
    """

    :param payload:
    :param current_user:
    :param service:
    :return:
    """
    try:
        profile = await service.create_driver_profile(current_user, payload)
        return profile
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.get("/me", response_model=DriverRead)
async def get_my_driver_profile(
        current_user: UserRead = Depends(get_current_user),
        service: DriverService = Depends(get_driver_service),
):
    """
    Get the logged-in user's driving profile.
    """
    try:
        profile = await service.get_driver_profile(current_user.id)
        return profile
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/", response_model=DriverRead)
async def get_driver_profile_by_id(
        current_user: UserRead = Depends(get_current_user),
        service: DriverService = Depends(get_driver_service),
):
    """
    Get any public driver profile by User ID.
    """
    try:
        profile = await service.get_driver_profile(current_user.id)
        return profile
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/", response_model=DriverRead)
async def update_my_driver_profile(
        payload: DriverUpdate,
        current_user: UserRead = Depends(get_current_user),
        service: DriverService = Depends(get_driver_service),
):
    """

    :param payload:
    :param current_user:
    :param service:
    :return:
    """
    try:
        updated_profile = await service.update_driver_profile(current_user, payload)
        return updated_profile
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


def get_ride_service(db: AsyncSession = Depends(get_session)):
    return RideService(db)

@router.post("/start", response_model=RideRead, status_code=status.HTTP_201_CREATED)
async def start_ride(
        payload: RideCreate,
        current_user: UserRead = Depends(get_current_user),
        service: RideService = Depends(get_ride_service),
):
    """

    :param payload:
    :param current_user:
    :param service:
    :return:
    """
    try:
        ride = await service.start_ride(current_user, payload)
        return ride
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@router.post("/{ride_id}/complete", response_model=RideRead)
async def complete_ride(
        ride_id: uuid.UUID,
        payload: RideComplete,
        current_user: UserRead = Depends(get_current_user),
        service: RideService = Depends(get_ride_service),
):
    """
    Ends the ride.
    Payload Example: { "success": true, "earnings": 50.0 }
    """
    try:
        ride = await service.complete_ride(current_user, ride_id, payload)
        return ride
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))





def get_location_service(db: AsyncSession = Depends(get_session)):
    return LocationService(db)


def get_driver_service(db: AsyncSession = Depends(get_session)):
    return DriverService(db)


@router.post("/ping")
async def ping_location(
        payload: LocationUpdate,
        current_user: UserRead = Depends(get_current_user),
        loc_service: LocationService = Depends(get_location_service),
        driver_service: DriverService = Depends(get_driver_service),
):
    """
    Drivers call this every 10-30 seconds to update where they are.
    """
    driver_profile = await driver_service.get_driver_profile(current_user.id)

    await loc_service.update_driver_location(driver_profile.id, payload)
    return {"status": "updated"}


@router.get("/nearby", response_model=List[DriverNearbyResponse])
async def get_drivers_nearby(
        latitude: float,
        longitude: float,
        radius: float = 5.0,
        current_user: UserRead = Depends(get_current_user),
        service: LocationService = Depends(get_location_service),
):
    """
    Returns list of active drivers within 'radius' km, sorted by distance.
    """
    if not current_user:
        raise HTTPException(status_code=403, detail="Authentication required")
    else:
        return await service.find_nearby_drivers(latitude, longitude, radius)