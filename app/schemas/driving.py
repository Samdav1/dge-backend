import uuid
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel
from app.models.driving import DriverRank, DriverStatus, RideStatus


class DriverBase(SQLModel):
    car_name: str
    car_model: str
    plate_number: str

class DriverCreate(DriverBase):
    pass

class DriverUpdate(SQLModel):
    car_name: Optional[str] = None
    car_model: Optional[str] = None
    plate_number: Optional[str] = None

class DriverRead(DriverBase):
    id: uuid.UUID
    user_id: uuid.UUID
    successful_rides: int
    total_rides: int
    failed_rides: int
    rank: DriverRank
    status: DriverStatus


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


class LocationUpdate(SQLModel):
    latitude: float
    longitude: float

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

