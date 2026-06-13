import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import Column, String, Integer, TIMESTAMP, func, Float, DateTime, Boolean, Enum as SAEnum
from sqlmodel import SQLModel, Field, Relationship
import enum


class DriverStatus(str, enum.Enum):
    ACTIVE = "active"
    PENDING = "pending"
    SUSPENDED = "suspended"
    BANNED = "banned"


class DriverRank(str, enum.Enum):
    STARTER = "starter"
    EXPERIENCED = "experienced"
    EXPERT = "expert"
    LEGEND = "legend"


class DriverProfile(SQLModel, table=True):
    __tablename__ = "driver_profiles"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True,
        nullable=False,
    )

    user_id: uuid.UUID = Field(foreign_key="users.id", unique=True, index=True, nullable=False)

    car_name: str = Field(max_length=255, nullable=False)
    car_model: str = Field(max_length=255, nullable=False)
    plate_number: str = Field(max_length=255, nullable=True)

    successful_rides: int = Field(default=0, nullable=False)
    total_rides: int = Field(default=0, nullable=False)
    failed_rides: int = Field(default=0, nullable=False)

    rank: DriverRank = Field(default=DriverRank.STARTER, nullable=False)
    status: DriverStatus = Field(default=DriverStatus.PENDING, nullable=False)

    created_at: datetime = Field(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=func.now()
        )
    )

    updated_at: datetime = Field(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=func.now(),
            onupdate=func.now()
        )
    )

    user: "Users" = Relationship(back_populates="driver_profile")


# ---------------------------------------------------------------------------
# Legacy ride model (driver personal log — preserved for backward compat)
# ---------------------------------------------------------------------------

class RideStatus(str, enum.Enum):
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Ride(SQLModel, table=True):
    __tablename__ = "rides"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    driver_id: uuid.UUID = Field(foreign_key="driver_profiles.id", index=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)  # The user who owns the driver profile

    start_location: str = Field(nullable=False)
    destination: str = Field(nullable=False)

    status: RideStatus = Field(default=RideStatus.STARTED)

    start_time: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False))
    end_time: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False))

    earnings: float = Field(default=0.0)


# ---------------------------------------------------------------------------
# Real-time driver location (high-write table — mirrored to Redis GEO)
# ---------------------------------------------------------------------------

class DriverLocation(SQLModel, table=True):
    __tablename__ = "driver_locations"

    driver_id: uuid.UUID = Field(
        foreign_key="driver_profiles.id",
        primary_key=True,
        nullable=False
    )

    latitude: float = Field(sa_column=Column(Float, nullable=False))
    longitude: float = Field(sa_column=Column(Float, nullable=False))

    # Matching engine uses this flag — set False when driver has an active trip
    is_available: bool = Field(
        sa_column=Column(Boolean, nullable=False, server_default="true"),
        default=True
    )

    updated_at: datetime = Field(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=func.now(),
            onupdate=func.now()
        )
    )


# ---------------------------------------------------------------------------
# Trip — the full rider-facing ride-request lifecycle
# ---------------------------------------------------------------------------

class TripStatus(str, enum.Enum):
    PENDING = "pending"               # Rider requested, waiting for driver to accept
    EN_ROUTE = "en_route"             # Driver accepted, en-route to pickup
    ARRIVED = "arrived"               # Driver arrived at pickup
    AWAITING_CONFIRMATION = "awaiting_confirmation" # Driver started trip, waiting for rider
    IN_PROGRESS = "in_progress"       # Trip officially started
    ACTIVE = "active"                 # (Legacy) Driver accepted, en-route / trip in progress
    COMPLETED = "completed"           # Trip finished, fare settled
    CANCELLED = "cancelled"           # Rider or driver cancelled before completion


class Trip(SQLModel, table=True):
    __tablename__ = "trips"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)

    # Parties
    rider_id: uuid.UUID = Field(foreign_key="users.id", index=True, nullable=False)
    driver_id: Optional[uuid.UUID] = Field(
        foreign_key="driver_profiles.id", index=True, nullable=True, default=None
    )

    # Locations
    pickup_lat: float = Field(sa_column=Column(Float, nullable=False))
    pickup_lng: float = Field(sa_column=Column(Float, nullable=False))
    dropoff_lat: float = Field(sa_column=Column(Float, nullable=False))
    dropoff_lng: float = Field(sa_column=Column(Float, nullable=False))
    pickup_address: Optional[str] = Field(default=None, nullable=True, max_length=512)
    dropoff_address: Optional[str] = Field(default=None, nullable=True, max_length=512)

    # Pricing
    distance_km: float = Field(default=0.0, sa_column=Column(Float, nullable=False, server_default="0"))
    estimated_fare: float = Field(default=0.0, sa_column=Column(Float, nullable=False, server_default="0"))
    final_fare: Optional[float] = Field(default=None, nullable=True)
    surge_multiplier: float = Field(
        default=1.0, sa_column=Column(Float, nullable=False, server_default="1.0")
    )

    # State machine
    status: TripStatus = Field(default=TripStatus.PENDING, nullable=False)

    # Timestamps
    requested_at: datetime = Field(
        sa_column=Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    )
    accepted_at: Optional[datetime] = Field(
        sa_column=Column(TIMESTAMP(timezone=True), nullable=True), default=None
    )
    completed_at: Optional[datetime] = Field(
        sa_column=Column(TIMESTAMP(timezone=True), nullable=True), default=None
    )
