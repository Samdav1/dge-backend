import uuid
from datetime import datetime
from typing import Optional, List
from sqlmodel import SQLModel
from app.models.driving import DriverRank, DriverStatus, RideStatus, TripStatus


# ---------------------------------------------------------------------------
# Driver profile schemas
# ---------------------------------------------------------------------------

class DriverBase(SQLModel):
    car_name: str
    car_model: str
    plate_number: str
    vehicle_type: Optional[str] = "car"
    car_picture_url: Optional[str] = None
    license_number: Optional[str] = None
    license_picture_url: Optional[str] = None

class DriverCreate(DriverBase):
    pass

class DriverUpdate(SQLModel):
    car_name: Optional[str] = None
    car_model: Optional[str] = None
    plate_number: Optional[str] = None
    vehicle_type: Optional[str] = None
    car_picture_url: Optional[str] = None
    license_number: Optional[str] = None
    license_picture_url: Optional[str] = None
    license_status: Optional[str] = None
    license_rejection_reason: Optional[str] = None

class DriverRead(DriverBase):
    id: uuid.UUID
    user_id: uuid.UUID
    successful_rides: int
    total_rides: int
    failed_rides: int
    rank: DriverRank
    status: DriverStatus
    vehicle_type: str
    car_picture_url: Optional[str] = None
    license_status: str
    license_rejection_reason: Optional[str] = None


# ---------------------------------------------------------------------------
# Legacy ride schemas (preserved for backward compat)
# ---------------------------------------------------------------------------

class RideBase(SQLModel):
    start_location: str
    destination: str

class RideCreate(RideBase):
    pass

class RideComplete(SQLModel):
    success: bool
    earnings: Optional[float] = 0.0

class RideRead(RideBase):
    id: uuid.UUID
    driver_id: uuid.UUID
    status: RideStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    earnings: float


# ---------------------------------------------------------------------------
# GPS / Location schemas
# ---------------------------------------------------------------------------

class LocationUpdate(SQLModel):
    """Legacy — kept so existing ping endpoint still works."""
    latitude: float
    longitude: float

class LocationPing(SQLModel):
    """
    Driver GPS ping payload.
    Sent every 3-5 seconds while a trip is ACTIVE.
    The server writes to Redis and pushes the update to the rider via WebSocket.
    """
    latitude: float
    longitude: float
    is_available: bool = True


class LocationSearch(SQLModel):
    latitude: float
    longitude: float
    radius_km: float = 5.0

class DriverNearbyResponse(SQLModel):
    driver_id: uuid.UUID
    latitude: float
    longitude: float
    distance_km: float
    car_name: str
    driver_name: str = "Driver"
    rating: float = 5.0
    driver_avatar: Optional[str] = None
    supported_vehicles: List[str] = []
    is_online: bool = True
    is_available: bool = True
    is_booked: bool = False
    status: str = "active"
    booking_status: str = "available" # "available", "booked", "offline", "inactive"



# ---------------------------------------------------------------------------
# Trip schemas  (the new rider-facing ride-request lifecycle)
# ---------------------------------------------------------------------------

class TripRequest(SQLModel):
    """Rider sends this to request a ride."""
    pickup_lat: float
    pickup_lng: float
    dropoff_lat: float
    dropoff_lng: float
    pickup_address: Optional[str] = None
    dropoff_address: Optional[str] = None
    surge_multiplier: float = 1.0
    driver_id: Optional[uuid.UUID] = None
    negotiated_fare: Optional[float] = None
    vehicle_type: Optional[str] = "car"

class TripRead(SQLModel):
    """Full trip state returned to both rider and driver."""
    id: uuid.UUID
    rider_id: uuid.UUID
    driver_id: Optional[uuid.UUID] = None
    driver_user_id: Optional[uuid.UUID] = None
    pickup_lat: float
    pickup_lng: float
    dropoff_lat: float
    dropoff_lng: float
    pickup_address: Optional[str] = None
    dropoff_address: Optional[str] = None
    distance_km: float
    estimated_fare: float
    final_fare: Optional[float] = None
    negotiated_fare: Optional[float] = None
    surge_multiplier: float
    status: TripStatus
    requested_at: datetime
    accepted_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    driver_name: Optional[str] = None
    driver_avatar: Optional[str] = None
    rider_name: Optional[str] = None
    rider_avatar: Optional[str] = None
    vehicle_type: Optional[str] = "car"

class TripAccept(SQLModel):
    """Driver sends this to accept a pending trip."""
    trip_id: uuid.UUID

class TripCancel(SQLModel):
    """Rider or driver sends this to cancel a pending/active trip."""
    trip_id: uuid.UUID
    reason: Optional[str] = None

class TripComplete(SQLModel):
    """Driver sends this when the trip ends."""
    trip_id: uuid.UUID
    final_fare: Optional[float] = None   # Override fare if needed (e.g. tolls)

class FareEstimateResponse(SQLModel):
    """Returned immediately when a ride is requested, before a driver accepts."""
    distance_km: float
    base_fare: float
    distance_charge: float
    surge_multiplier: float
    estimated_fare: float

class TripReviewCreate(SQLModel):
    rating: int
    comment: str


class TripCounter(SQLModel):
    counter_fare: float

class DriverVehicleCreate(SQLModel):
    vehicle_type: str
    license_number: str
    picture_url: Optional[str] = None

class DriverVehicleRead(SQLModel):
    id: uuid.UUID
    driver_id: uuid.UUID
    vehicle_type: str
    license_number: str
    picture_url: Optional[str] = None
    is_verified: bool
    created_at: datetime
