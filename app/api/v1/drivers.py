"""
driving.py  (API v1)
--------------------
All driving-related HTTP endpoints:

  Driver profile management
  ├── POST   /drivers/            → Create driver profile
  ├── GET    /drivers/me          → Get my driver profile
  └── PATCH  /drivers/            → Update my driver profile

  GPS ping  (high-frequency, Redis write-through)
  └── POST   /drivers/ping        → Driver GPS ping (writes Redis + pushes rider WS)

  Nearby drivers  (now Redis-backed, not SQL Haversine)
  └── GET    /drivers/nearby      → Find available drivers near a coordinate

  Legacy ride log  (driver personal record, backward compat)
  ├── POST   /drivers/start       → Driver manually starts a ride record
  └── POST   /drivers/{ride_id}/complete  → Complete a ride record

  Trip lifecycle  (full rider-facing flow)
  ├── POST   /drivers/trips/request           → Rider requests a ride
  ├── POST   /drivers/trips/{id}/accept       → Driver accepts trip
  ├── POST   /drivers/trips/{id}/cancel       → Rider or driver cancels
  ├── POST   /drivers/trips/{id}/complete     → Driver completes trip
  ├── GET    /drivers/trips/{id}              → Get trip by ID
  ├── GET    /drivers/trips/my/rider          → Rider trip history
  └── GET    /drivers/trips/my/driver         → Driver trip history
"""

import uuid
from typing import List, Optional

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.db.session import get_session
from app.dependencies.auth import get_current_user
from app.schemas.driving import (
    DriverCreate, DriverRead, DriverUpdate,
    RideCreate, RideRead, RideComplete,
    DriverNearbyResponse, LocationUpdate, LocationPing,
    TripRequest, TripRead, TripAccept, TripCancel, TripComplete,
    FareEstimateResponse,
)
from app.schemas.user import UserRead
from app.services.driving_service import DriverService, RideService, LocationService
from app.services.matching_service import MatchingService
from app.services.redis_location import RedisLocationService
from app.services.pricing_service import calculate_trip_fare
from app.repositories.trip_repo import TripRepository

router = APIRouter(tags=["Drivers"])


# ---------------------------------------------------------------------------
# Dependency factories
# ---------------------------------------------------------------------------

def get_driver_service(db: AsyncSession = Depends(get_session)) -> DriverService:
    return DriverService(db)


def get_ride_service(db: AsyncSession = Depends(get_session)) -> RideService:
    return RideService(db)


def get_location_service(db: AsyncSession = Depends(get_session)) -> LocationService:
    return LocationService(db)


def get_redis_location() -> RedisLocationService:
    """Return a RedisLocationService using the app-wide Redis connection."""
    # Import the singleton manager to reuse its Redis client
    from app.main import manager
    if manager._redis is None:
        raise HTTPException(status_code=503, detail="Redis not available")
    return RedisLocationService(manager._redis)


def get_matching_service(
    db: AsyncSession = Depends(get_session),
    redis_loc: RedisLocationService = Depends(get_redis_location),
) -> MatchingService:
    from app.main import manager
    return MatchingService(session=db, redis_location=redis_loc, connection_manager=manager)


def get_trip_repo(db: AsyncSession = Depends(get_session)) -> TripRepository:
    return TripRepository(db)


# ===========================================================================
# Driver profile endpoints
# ===========================================================================

@router.post("/", response_model=DriverRead, status_code=status.HTTP_201_CREATED)
async def create_driver_profile(
    payload: DriverCreate,
    current_user: UserRead = Depends(get_current_user),
    service: DriverService = Depends(get_driver_service),
):
    """Register the current user as a driver by creating their driver profile."""
    try:
        return await service.create_driver_profile(current_user, payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.get("/me", response_model=DriverRead)
async def get_my_driver_profile(
    current_user: UserRead = Depends(get_current_user),
    service: DriverService = Depends(get_driver_service),
):
    """Get the logged-in user's driver profile."""
    try:
        return await service.get_driver_profile(current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/", response_model=DriverRead)
async def update_my_driver_profile(
    payload: DriverUpdate,
    current_user: UserRead = Depends(get_current_user),
    service: DriverService = Depends(get_driver_service),
):
    """Update the current user's driver profile (car details, plate, etc.)."""
    try:
        return await service.update_driver_profile(current_user, payload)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


# ===========================================================================
# GPS ping  (high-frequency hot path)
# ===========================================================================

@router.post("/ping", status_code=status.HTTP_200_OK)
async def ping_location(
    payload: LocationPing,
    current_user: UserRead = Depends(get_current_user),
    driver_service: DriverService = Depends(get_driver_service),
    matching_service: MatchingService = Depends(get_matching_service),
):
    """
    Driver GPS ping — called every 3-5 seconds.

    Writes position to Redis GEO index (fast, in-memory).
    If the driver has an ACTIVE trip, immediately pushes the location
    to the rider's WebSocket channel.
    """
    try:
        driver_profile = await driver_service.get_driver_profile(current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    await matching_service.handle_gps_ping(
        driver_id=driver_profile.id,
        lat=payload.latitude,
        lng=payload.longitude,
    )
    return {"status": "ok"}


# ===========================================================================
# Nearby drivers  (Redis GEO-backed)
# ===========================================================================

@router.get("/nearby", response_model=List[DriverNearbyResponse])
async def get_drivers_nearby(
    latitude: float = Query(..., description="Rider's current latitude"),
    longitude: float = Query(..., description="Rider's current longitude"),
    radius: float = Query(5.0, description="Search radius in kilometres"),
    current_user: UserRead = Depends(get_current_user),
    redis_loc: RedisLocationService = Depends(get_redis_location),
):
    """
    Return available drivers within `radius` km, sorted nearest-first.
    Queries Redis GEO — O(log N), no SQL scan.
    """
    nearby = await redis_loc.find_nearby_available(latitude, longitude, radius_km=radius)
    return [
        DriverNearbyResponse(
            driver_id=uuid.UUID(d["driver_id"]),
            latitude=0.0,   # position intentionally hidden from public endpoint
            longitude=0.0,
            distance_km=d["distance_km"],
            car_name="",    # enriched by client via separate /drivers/{id} call if needed
        )
        for d in nearby
    ]


# ===========================================================================
# Legacy ride log  (driver personal record)
# ===========================================================================

@router.post("/start", response_model=RideRead, status_code=status.HTTP_201_CREATED)
async def start_ride(
    payload: RideCreate,
    current_user: UserRead = Depends(get_current_user),
    service: RideService = Depends(get_ride_service),
):
    """(Legacy) Driver manually starts a ride record in their personal log."""
    try:
        return await service.start_ride(current_user, payload)
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
    """(Legacy) Completes the driver's personal ride log record."""
    try:
        return await service.complete_ride(current_user, ride_id, payload)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===========================================================================
# Trip lifecycle  (full rider-facing flow)
# ===========================================================================

@router.post(
    "/trips/request",
    response_model=TripRead,
    status_code=status.HTTP_201_CREATED,
    summary="Rider: Request a ride",
)
async def request_ride(
    payload: TripRequest,
    current_user: UserRead = Depends(get_current_user),
    matching: MatchingService = Depends(get_matching_service),
):
    """
    Rider requests a ride. The matching engine:
    1. Queries Redis GEO for the nearest available driver.
    2. Calculates the estimated fare.
    3. Creates a PENDING Trip record.
    4. Pushes a ride_request WebSocket event to the driver.
    5. Starts a 30-second acceptance timeout.

    Returns the newly created Trip (status=PENDING, estimated_fare populated).
    """
    try:
        trip = await matching.request_ride(
            rider_id=current_user.id,
            pickup_lat=payload.pickup_lat,
            pickup_lng=payload.pickup_lng,
            dropoff_lat=payload.dropoff_lat,
            dropoff_lng=payload.dropoff_lng,
            pickup_address=payload.pickup_address,
            dropoff_address=payload.dropoff_address,
            surge_multiplier=payload.surge_multiplier,
        )
        return trip
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.post(
    "/trips/{trip_id}/accept",
    response_model=TripRead,
    summary="Driver: Accept a ride request",
)
async def accept_trip(
    trip_id: uuid.UUID,
    current_user: UserRead = Depends(get_current_user),
    driver_service: DriverService = Depends(get_driver_service),
    matching: MatchingService = Depends(get_matching_service),
):
    """
    Driver accepts a PENDING trip.
    Transitions: PENDING → ACTIVE.
    Notifies the rider via WebSocket (ride_accepted event).
    """
    try:
        driver_profile = await driver_service.get_driver_profile(current_user.id)
        trip = await matching.accept_trip(driver_id=driver_profile.id, trip_id=trip_id)
        return trip
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.post(
    "/trips/{trip_id}/cancel",
    response_model=TripRead,
    summary="Rider or Driver: Cancel a trip",
)
async def cancel_trip(
    trip_id: uuid.UUID,
    payload: Optional[TripCancel] = None,
    current_user: UserRead = Depends(get_current_user),
    matching: MatchingService = Depends(get_matching_service),
):
    """
    Cancel a PENDING or ACTIVE trip.
    Notifies the other party via WebSocket (ride_cancelled event).
    Re-enables the driver's availability in Redis.
    """
    try:
        reason = payload.reason if payload else None
        trip = await matching.cancel_trip(
            trip_id=trip_id,
            cancelled_by_id=current_user.id,
            reason=reason,
        )
        return trip
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.post(
    "/trips/{trip_id}/complete",
    response_model=TripRead,
    summary="Driver: Complete a trip",
)
async def complete_trip(
    trip_id: uuid.UUID,
    payload: Optional[TripComplete] = None,
    current_user: UserRead = Depends(get_current_user),
    driver_service: DriverService = Depends(get_driver_service),
    matching: MatchingService = Depends(get_matching_service),
):
    """
    Driver marks the trip as COMPLETED.
    Sets the final fare, re-enables driver availability in Redis,
    and notifies both parties (ride_completed event).
    """
    try:
        driver_profile = await driver_service.get_driver_profile(current_user.id)
        final_fare = payload.final_fare if payload else None
        trip = await matching.complete_trip(
            driver_id=driver_profile.id,
            trip_id=trip_id,
            final_fare=final_fare,
        )
        return trip
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.get(
    "/trips/my/rider",
    response_model=List[TripRead],
    summary="Rider: My trip history",
)
async def get_my_trips_as_rider(
    limit: int = Query(20, ge=1, le=100),
    current_user: UserRead = Depends(get_current_user),
    repo: TripRepository = Depends(get_trip_repo),
):
    """Returns the authenticated user's trip history as a rider (newest first)."""
    return await repo.get_trips_for_rider(current_user.id, limit=limit)


@router.get(
    "/trips/my/driver",
    response_model=List[TripRead],
    summary="Driver: My trip history",
)
async def get_my_trips_as_driver(
    limit: int = Query(20, ge=1, le=100),
    current_user: UserRead = Depends(get_current_user),
    driver_service: DriverService = Depends(get_driver_service),
    repo: TripRepository = Depends(get_trip_repo),
):
    """Returns the driver's trip history (newest first)."""
    try:
        driver_profile = await driver_service.get_driver_profile(current_user.id)
        return await repo.get_trips_for_driver(driver_profile.id, limit=limit)
    except ValueError:
        return []


@router.get(
    "/trips/{trip_id}",
    response_model=TripRead,
    summary="Get trip by ID",
)
async def get_trip(
    trip_id: uuid.UUID,
    current_user: UserRead = Depends(get_current_user),
    repo: TripRepository = Depends(get_trip_repo),
):
    """Fetch a trip by ID. Returns 404 if not found or 403 if the user is not a party."""
    trip = await repo.get_by_id(trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    # Only rider or the assigned driver can view the trip
    if trip.rider_id != current_user.id and trip.driver_id != current_user.id:
        raise HTTPException(status_code=403, detail="You are not a party to this trip")
    return trip