import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import Column, String, Integer, TIMESTAMP, func, Float, DateTime
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
        sa_column=Column(DateTime(timezone=True),
                         nullable=False))
    end_time: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True),
                         nullable=False))

    earnings: float = Field(default=0.0)


class DriverLocation(SQLModel, table=True):
    __tablename__ = "driver_locations"

    driver_id: uuid.UUID = Field(
        foreign_key="driver_profiles.id",
        primary_key=True,
        nullable=False
    )

    latitude: float = Field(sa_column=Column(Float, nullable=False))
    longitude: float = Field(sa_column=Column(Float, nullable=False))

    updated_at: datetime = Field(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=func.now(),
            onupdate=func.now()
        )
    )