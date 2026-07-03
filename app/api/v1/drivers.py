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
from fastapi import APIRouter, Depends, HTTPException, Query, status, File, UploadFile
from sqlmodel.ext.asyncio.session import AsyncSession

from app.db.session import get_session
from app.dependencies.auth import get_current_user
from app.schemas.driving import (
    DriverCreate, DriverRead, DriverUpdate,
    RideCreate, RideRead, RideComplete,
    DriverNearbyResponse, LocationUpdate, LocationPing,
    TripRequest, TripRead, TripAccept, TripCancel, TripComplete,
    FareEstimateResponse, TripReviewCreate, TripCounter,
    DriverVehicleCreate, DriverVehicleRead,
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
    from app.dependencies.socket_connection import manager
    if manager._redis is None:
        raise HTTPException(status_code=503, detail="Redis not available")
    return RedisLocationService(manager._redis)


def get_matching_service(
    db: AsyncSession = Depends(get_session),
    redis_loc: RedisLocationService = Depends(get_redis_location),
) -> MatchingService:
    from app.dependencies.socket_connection import manager
    return MatchingService(session=db, redis_location=redis_loc, connection_manager=manager)


def get_trip_repo(db: AsyncSession = Depends(get_session)) -> TripRepository:
    return TripRepository(db)


async def get_trip_read_with_details(trip, db: AsyncSession) -> TripRead:
    trip_read = TripRead.model_validate(trip)
    
    from app.models.user import Users
    from app.models.profile import Profile
    from sqlmodel import select

    # 1. Populate Rider Details
    rider_user = await db.get(Users, trip.rider_id)
    if rider_user:
        trip_read.rider_name = rider_user.username
        stmt = select(Profile).where(Profile.user_id == trip.rider_id)
        res = await db.execute(stmt)
        rider_prof = res.scalars().first()
        if rider_prof:
            if rider_prof.avatar_url:
                trip_read.rider_avatar = rider_prof.avatar_url
            if rider_prof.first_name:
                trip_read.rider_name = f"{rider_prof.first_name} {rider_prof.last_name or ''}".strip()
                
    # 2. Populate Driver Details
    if trip.driver_id:
        from app.models.driving import DriverProfile
        driver_prof_record = await db.get(DriverProfile, trip.driver_id)
        if driver_prof_record:
            trip_read.driver_user_id = driver_prof_record.user_id
            driver_user = await db.get(Users, driver_prof_record.user_id)
            if driver_user:
                trip_read.driver_name = driver_user.username
                stmt = select(Profile).where(Profile.user_id == driver_prof_record.user_id)
                res = await db.execute(stmt)
                driver_prof = res.scalars().first()
                if driver_prof:
                    if driver_prof.avatar_url:
                        trip_read.driver_avatar = driver_prof.avatar_url
                    if driver_prof.first_name:
                        trip_read.driver_name = f"{driver_prof.first_name} {driver_prof.last_name or ''}".strip()
                        
    return trip_read


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


@router.patch("/car-picture", response_model=DriverRead)
async def upload_driver_car_picture(
    file: UploadFile = File(...),
    current_user: UserRead = Depends(get_current_user),
    service: DriverService = Depends(get_driver_service),
    db: AsyncSession = Depends(get_session),
):
    """Upload a vehicle/card picture for the driver's profile."""
    try:
        driver_profile = await service.get_driver_profile(current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    from app.dependencies.file_handler import save_avatar
    picture_path = await save_avatar(file)
    if not picture_path:
        raise HTTPException(status_code=400, detail="Failed to save vehicle picture file.")

    driver_profile.car_picture_url = picture_path
    db.add(driver_profile)
    await db.commit()
    await db.refresh(driver_profile)
    return driver_profile


@router.patch("/license-picture", response_model=DriverRead)
async def upload_driver_license_picture(
    file: UploadFile = File(...),
    current_user: UserRead = Depends(get_current_user),
    service: DriverService = Depends(get_driver_service),
    db: AsyncSession = Depends(get_session),
):
    """Upload a driver's license picture for verification."""
    try:
        driver_profile = await service.get_driver_profile(current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    from app.dependencies.file_handler import save_kyc_image
    picture_path = await save_kyc_image(file)
    if not picture_path:
        raise HTTPException(status_code=400, detail="Failed to save license picture file.")

    driver_profile.license_picture_url = picture_path
    if driver_profile.license_number:
        driver_profile.license_status = "pending"
        driver_profile.license_rejection_reason = None
        
    db.add(driver_profile)
    await db.commit()
    await db.refresh(driver_profile)
    return driver_profile


@router.post("/vehicles", response_model=DriverVehicleRead, status_code=status.HTTP_201_CREATED)
async def register_driver_vehicle(
    payload: DriverVehicleCreate,
    current_user: UserRead = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
    service: DriverService = Depends(get_driver_service),
):
    """Register and verify a new vehicle for the logged-in driver."""
    driver_profile = await service.repo.get_by_user_id(current_user.id)
    if not driver_profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Driver profile not found.")
    
    from app.models.driving import DriverVehicle
    db_veh = DriverVehicle(
        driver_id=driver_profile.id,
        vehicle_type=payload.vehicle_type,
        license_number=payload.license_number,
        picture_url=payload.picture_url,
        is_verified=True  # Immediately verified for testing/usability
    )
    db.add(db_veh)
    await db.commit()
    await db.refresh(db_veh)
    return db_veh


@router.get("/vehicles", response_model=List[DriverVehicleRead])
async def list_driver_vehicles(
    current_user: UserRead = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
    service: DriverService = Depends(get_driver_service),
):
    """List all registered vehicles for the logged-in driver."""
    driver_profile = await service.repo.get_by_user_id(current_user.id)
    if not driver_profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Driver profile not found.")
    
    from sqlmodel import select
    from app.models.driving import DriverVehicle
    stmt = select(DriverVehicle).where(DriverVehicle.driver_id == driver_profile.id)
    res = await db.exec(stmt)
    return res.all()


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

    driver_details = {
        "name": getattr(current_user, 'username', 'Driver'),
        "car_name": driver_profile.car_name,
        "car_model": driver_profile.car_model,
        "rank": driver_profile.rank.value,
        "rating": 4.8  # Default mock rating for now
    }

    await matching_service.handle_gps_ping(
        driver_id=driver_profile.id,
        lat=payload.latitude,
        lng=payload.longitude,
        is_available=payload.is_available,
        driver_details=driver_details
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
    driver_service: DriverService = Depends(get_driver_service),
    db: AsyncSession = Depends(get_session),
):
    """
    Return available drivers within `radius` km, sorted nearest-first.
    Queries Redis GEO — O(log N), no SQL scan.
    """
    from app.models.user import Users
    nearby = await redis_loc.find_nearby_available(latitude, longitude, radius_km=radius)
    response = []
    for d in nearby:
        d_id = uuid.UUID(d["driver_id"])
        profile = await driver_service.repo.get_by_id(d_id)
        user_record = await db.get(Users, profile.user_id) if profile else None
        driver_name = user_record.username if user_record else "Driver"
        car_name = f"{profile.car_name} {profile.car_model}" if profile else ""
        # Get driver average rating from reviews
        rating = 5.0
        if profile:
            from app.models.portfolio import UserPortfolio, Review
            from sqlmodel import select, func
            portfolio_res = await db.execute(
                select(UserPortfolio).where(UserPortfolio.user_id == profile.user_id)
            )
            portfolio = portfolio_res.scalars().first()
            if portfolio:
                avg_rating_res = await db.execute(
                    select(func.avg(Review.rating)).where(Review.portfolio_id == portfolio.id)
                )
                avg_val = avg_rating_res.scalar()
                if avg_val is not None:
                    rating = float(avg_val)

        # Get driver personal profile for avatar
        driver_avatar = None
        if profile:
            from app.models.profile import Profile
            from sqlmodel import select
            personal_prof_res = await db.execute(
                select(Profile).where(Profile.user_id == profile.user_id)
            )
            personal_prof = personal_prof_res.scalars().first()
            if personal_prof:
                driver_avatar = personal_prof.avatar_url
                if personal_prof.first_name:
                    driver_name = f"{personal_prof.first_name} {personal_prof.last_name or ''}".strip()

        # Get supported vehicles
        supported_vehicles = []
        if profile:
            from app.models.driving import DriverVehicle
            from sqlmodel import select
            veh_res = await db.execute(
                select(DriverVehicle).where(
                    DriverVehicle.driver_id == profile.id,
                    DriverVehicle.is_verified == True
                )
            )
            vehicles_list = veh_res.scalars().all()
            supported_vehicles = [v.vehicle_type.lower() for v in vehicles_list]
            if not supported_vehicles:
                supported_vehicles = [getattr(profile, "vehicle_type", "car").lower()]

        response.append(
            DriverNearbyResponse(
                driver_id=d_id,
                latitude=d["lat"] if "lat" in d else 0.0,
                longitude=d["lng"] if "lng" in d else 0.0,
                distance_km=d["distance_km"],
                car_name=car_name,
                driver_name=driver_name,
                rating=rating,
                driver_avatar=driver_avatar,
                supported_vehicles=supported_vehicles,
            )
        )
    return response


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
            driver_id=payload.driver_id,
            negotiated_fare=payload.negotiated_fare,
            vehicle_type=payload.vehicle_type or "car",
        )
        return trip
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.post(
    "/trips/broadcast_intent",
    status_code=status.HTTP_200_OK,
    summary="Rider: Broadcast intent to book a ride to nearby drivers",
)
async def broadcast_intent(
    payload: TripRequest,
    current_user: UserRead = Depends(get_current_user),
    matching: MatchingService = Depends(get_matching_service),
):
    """
    Rider clicks 'See Available Drivers'.
    This finds nearby available drivers and pushes an 'incoming_ride_intent'
    WebSocket message to them to notify them that a rider is looking.
    """
    try:
        result = await matching.broadcast_ride_intent(
            rider_id=current_user.id,
            pickup_lat=payload.pickup_lat,
            pickup_lng=payload.pickup_lng,
            dropoff_lat=payload.dropoff_lat,
            dropoff_lng=payload.dropoff_lng,
            pickup_address=payload.pickup_address,
            dropoff_address=payload.dropoff_address,
            vehicle_type=payload.vehicle_type or "car",
        )
        return result
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
        trip_read = TripRead.model_validate(trip)
        trip_read.driver_user_id = driver_profile.user_id
        return trip_read
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.post(
    "/trips/{trip_id}/counter",
    response_model=TripRead,
    summary="Driver: Propose a counter-offer price for the ride",
)
async def counter_trip(
    trip_id: uuid.UUID,
    payload: TripCounter,
    current_user: UserRead = Depends(get_current_user),
    driver_service: DriverService = Depends(get_driver_service),
    matching: MatchingService = Depends(get_matching_service),
):
    try:
        driver_profile = await driver_service.get_driver_profile(current_user.id)
        trip = await matching.counter_offer(
            driver_id=driver_profile.id,
            trip_id=trip_id,
            counter_fare=payload.counter_fare
        )
        trip_read = TripRead.model_validate(trip)
        trip_read.driver_user_id = driver_profile.user_id
        return trip_read
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.post(
    "/trips/{trip_id}/accept_counter",
    response_model=TripRead,
    summary="Rider: Accept the driver's counter-offer price",
)
async def accept_counter(
    trip_id: uuid.UUID,
    current_user: UserRead = Depends(get_current_user),
    matching: MatchingService = Depends(get_matching_service),
    db: AsyncSession = Depends(get_session),
):
    try:
        trip = await matching.accept_counter(rider_id=current_user.id, trip_id=trip_id)
        trip_read = TripRead.model_validate(trip)
        if trip.driver_id:
            from app.repositories.driving import DriverRepository
            driver_repo = DriverRepository(db)
            driver_profile = await driver_repo.get_by_id(trip.driver_id)
            if driver_profile:
                trip_read.driver_user_id = driver_profile.user_id
        return trip_read
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.post(
    "/trips/{trip_id}/arrive",
    response_model=TripRead,
    summary="Driver: Mark as arrived at pickup",
)
async def arrive_at_pickup(
    trip_id: uuid.UUID,
    current_user: UserRead = Depends(get_current_user),
    driver_service: DriverService = Depends(get_driver_service),
    matching: MatchingService = Depends(get_matching_service),
):
    try:
        driver_profile = await driver_service.get_driver_profile(current_user.id)
        trip = await matching.arrive_at_pickup(driver_id=driver_profile.id, trip_id=trip_id)
        trip_read = TripRead.model_validate(trip)
        trip_read.driver_user_id = driver_profile.user_id
        return trip_read
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.post(
    "/trips/{trip_id}/start",
    response_model=TripRead,
    summary="Driver: Request to start the trip",
)
async def start_trip(
    trip_id: uuid.UUID,
    current_user: UserRead = Depends(get_current_user),
    driver_service: DriverService = Depends(get_driver_service),
    matching: MatchingService = Depends(get_matching_service),
):
    try:
        driver_profile = await driver_service.get_driver_profile(current_user.id)
        trip = await matching.start_trip(driver_id=driver_profile.id, trip_id=trip_id)
        trip_read = TripRead.model_validate(trip)
        trip_read.driver_user_id = driver_profile.user_id
        return trip_read
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.post(
    "/trips/{trip_id}/confirm_start",
    response_model=TripRead,
    summary="Rider: Confirm start of the trip",
)
async def confirm_start(
    trip_id: uuid.UUID,
    current_user: UserRead = Depends(get_current_user),
    matching: MatchingService = Depends(get_matching_service),
    driver_service: DriverService = Depends(get_driver_service),
):
    try:
        trip = await matching.confirm_start(rider_id=current_user.id, trip_id=trip_id)
        trip_read = TripRead.model_validate(trip)
        if trip.driver_id:
            try:
                driver_profile = await driver_service.get_driver_profile_by_id(trip.driver_id)
                trip_read.driver_user_id = driver_profile.user_id
            except Exception:
                pass
        return trip_read
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
    driver_service: DriverService = Depends(get_driver_service),
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
        trip_read = TripRead.model_validate(trip)
        if trip.driver_id:
            try:
                profile = await driver_service.get_driver_profile_by_id(trip.driver_id)
                trip_read.driver_user_id = profile.user_id
            except Exception:
                pass
        return trip_read
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
        trip_read = TripRead.model_validate(trip)
        trip_read.driver_user_id = driver_profile.user_id
        return trip_read
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.get(
    "/trips/active",
    response_model=Optional[TripRead],
    summary="Get active trip for current user",
)
async def get_active_trip(
    current_user: UserRead = Depends(get_current_user),
    driver_service: DriverService = Depends(get_driver_service),
    repo: TripRepository = Depends(get_trip_repo),
    db: AsyncSession = Depends(get_session),
):
    """
    Returns the user's current active or pending trip (either as rider or driver).
    If no active trip exists, returns None.
    """
    # Check if they have an active trip as a rider
    rider_trip = await repo.get_active_for_rider(current_user.id)
    if rider_trip:
        return await get_trip_read_with_details(rider_trip, db)

    # Check if they have an active trip as a driver
    try:
        driver_profile = await driver_service.get_driver_profile(current_user.id)
        if driver_profile:
            driver_trip = await repo.get_active_for_driver(driver_profile.id)
            if driver_trip:
                return await get_trip_read_with_details(driver_trip, db)

            # Optionally check pending trips for driver too
            pending_trip = await repo.get_pending_for_driver(driver_profile.id)
            if pending_trip:
                return await get_trip_read_with_details(pending_trip, db)
    except ValueError:
        pass

    return None


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
    driver_service: DriverService = Depends(get_driver_service),
    db: AsyncSession = Depends(get_session),
):
    """Fetch a trip by ID. Returns 404 if not found or 403 if the user is not a party."""
    trip = await repo.get_by_id(trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    driver_profile_id = None
    try:
        driver_profile = await driver_service.get_driver_profile(current_user.id)
        if driver_profile:
            driver_profile_id = driver_profile.id
    except Exception:
        pass

    # Only rider or the assigned driver can view the trip
    if trip.rider_id != current_user.id and (trip.driver_id is None or trip.driver_id != driver_profile_id):
        raise HTTPException(status_code=403, detail="You are not a party to this trip")

    return await get_trip_read_with_details(trip, db)


@router.post("/trips/{trip_id}/review", status_code=status.HTTP_201_CREATED)
async def review_trip(
    trip_id: uuid.UUID,
    payload: TripReviewCreate,
    current_user: UserRead = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    """
    Rider: Submit a review and rating for a completed trip.
    This creates/updates the driver's public portfolio and saves the review.
    """
    from sqlmodel import select
    from app.models.driving import Trip, DriverProfile
    from app.models.portfolio import UserPortfolio, PortfolioVisibility, Review

    trip = await db.get(Trip, trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    if trip.rider_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only review trips you took")

    if not trip.driver_id:
        raise HTTPException(status_code=400, detail="This trip has no driver")

    driver_profile = await db.get(DriverProfile, trip.driver_id)
    if not driver_profile:
        raise HTTPException(status_code=404, detail="Driver profile not found")

    driver_user_id = driver_profile.user_id

    # Find or create UserPortfolio for the driver
    portfolio_res = await db.execute(
        select(UserPortfolio).where(UserPortfolio.user_id == driver_user_id)
    )
    portfolio = portfolio_res.scalars().first()
    if not portfolio:
        # Get driver username to make a nice title
        from app.models.user import Users
        driver_user = await db.get(Users, driver_user_id)
        driver_username = driver_user.username if driver_user else "Driver"
        portfolio = UserPortfolio(
            user_id=driver_user_id,
            title=f"{driver_username}'s Service Portfolio",
            description="Driver's public ride-hailing services portfolio",
            visibility=PortfolioVisibility.public
        )
        db.add(portfolio)
        await db.commit()
        await db.refresh(portfolio)

    # Save the review
    new_review = Review(
        user_id=current_user.id,
        portfolio_id=portfolio.id,
        rating=payload.rating,
        comment=payload.comment
    )
    db.add(new_review)
    await db.commit()
    await db.refresh(new_review)

    return {"status": "success", "review_id": str(new_review.id)}


@router.get("/{driver_id}/public-profile")
async def get_driver_public_profile(
    driver_id: uuid.UUID,
    db: AsyncSession = Depends(get_session)
):
    """
    Get public details of a driver, including completed trips and all reviews received over time.
    """
    from sqlmodel import select
    from app.models.driving import DriverProfile, Trip, TripStatus
    from app.models.user import Users
    from app.models.profile import Profile
    from app.models.portfolio import UserPortfolio, Review

    driver_profile = await db.get(DriverProfile, driver_id)
    if not driver_profile:
        raise HTTPException(status_code=404, detail="Driver not found")

    # Fetch User & Profile
    driver_user = await db.get(Users, driver_profile.user_id)
    if not driver_user:
        raise HTTPException(status_code=404, detail="Driver user account not found")

    profile_res = await db.execute(select(Profile).where(Profile.user_id == driver_profile.user_id))
    driver_personal_profile = profile_res.scalars().first()

    driver_name = driver_personal_profile.first_name + " " + driver_personal_profile.last_name if (driver_personal_profile and driver_personal_profile.first_name) else driver_user.username
    driver_avatar = driver_personal_profile.avatar_url if driver_personal_profile else None

    # Fetch completed trips
    trips_res = await db.execute(
        select(Trip).where(Trip.driver_id == driver_id, Trip.status == TripStatus.COMPLETED).order_by(Trip.completed_at.desc())
    )
    completed_trips = trips_res.scalars().all()

    # Calculate stats dynamically
    successful_rides_count = len(completed_trips)
    
    total_rides_res = await db.execute(
        select(Trip).where(Trip.driver_id == driver_id)
    )
    total_rides_count = len(total_rides_res.scalars().all())
    
    # Update driver profile columns if they differ
    if driver_profile.successful_rides != successful_rides_count or driver_profile.total_rides != total_rides_count:
        driver_profile.successful_rides = successful_rides_count
        driver_profile.total_rides = total_rides_count
        
        # Check rank upgrade logic
        from app.models.driving import DriverRank
        from app.services.driving_service import RANK_THRESHOLDS
        
        new_rank = DriverRank.STARTER
        for rank, threshold in RANK_THRESHOLDS.items():
            if successful_rides_count >= threshold:
                new_rank = rank
                break
        driver_profile.rank = new_rank
        
        db.add(driver_profile)
        await db.commit()
        await db.refresh(driver_profile)

    # Fetch reviews via UserPortfolio
    portfolio_res = await db.execute(
        select(UserPortfolio).where(UserPortfolio.user_id == driver_profile.user_id)
    )
    portfolio = portfolio_res.scalars().first()

    reviews_list = []
    if portfolio:
        reviews_res = await db.execute(
            select(Review).where(Review.portfolio_id == portfolio.id).order_by(Review.created_at.desc())
        )
        reviews = reviews_res.scalars().all()

        for r in reviews:
            # Get reviewer's details
            reviewer_user = await db.get(Users, r.user_id)
            reviewer_name = reviewer_user.username if reviewer_user else "Anonymous"
            reviewer_avatar = None
            if reviewer_user:
                rev_prof_res = await db.execute(select(Profile).where(Profile.user_id == reviewer_user.id))
                rev_prof = rev_prof_res.scalars().first()
                if rev_prof:
                    if rev_prof.first_name:
                        reviewer_name = f"{rev_prof.first_name} {rev_prof.last_name or ''}".strip()
                    reviewer_avatar = rev_prof.avatar_url

            reviews_list.append({
                "id": str(r.id),
                "reviewer_name": reviewer_name,
                "reviewer_avatar": reviewer_avatar,
                "rating": r.rating,
                "comment": r.comment,
                "created_at": r.created_at.isoformat()
            })

    # Prepare response
    return {
        "driver_id": str(driver_id),
        "driver_name": driver_name,
        "driver_avatar": driver_avatar,
        "car_name": driver_profile.car_name,
        "car_model": driver_profile.car_model,
        "plate_number": driver_profile.plate_number,
        "successful_rides": driver_profile.successful_rides,
        "total_rides": driver_profile.total_rides,
        "rank": driver_profile.rank.value,
        "reviews": reviews_list,
        "completed_trips": [
            {
                "id": str(t.id),
                "pickup_address": t.pickup_address,
                "dropoff_address": t.dropoff_address,
                "completed_at": t.completed_at.isoformat() if t.completed_at else None,
                "distance_km": t.distance_km
            }
            for t in completed_trips
        ]
    }
