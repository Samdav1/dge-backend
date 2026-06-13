"""
trip_repo.py
------------
Data-access layer for the Trip model.
All state-machine transitions are validated at the service layer;
this repo only performs CRUD and filtered lookups.
"""

import uuid
from typing import Optional

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.driving import Trip, TripStatus


class TripRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    async def create(self, trip: Trip) -> Trip:
        self.session.add(trip)
        await self.session.commit()
        await self.session.refresh(trip)
        return trip

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def get_by_id(self, trip_id: uuid.UUID) -> Optional[Trip]:
        return await self.session.get(Trip, trip_id)

    async def get_active_for_rider(self, rider_id: uuid.UUID) -> Optional[Trip]:
        """Return the most recent non-terminal trip for a rider."""
        stmt = (
            select(Trip)
            .where(Trip.rider_id == rider_id)
            .where(Trip.status.in_([
                TripStatus.PENDING, TripStatus.ACTIVE,
                TripStatus.EN_ROUTE, TripStatus.ARRIVED,
                TripStatus.AWAITING_CONFIRMATION, TripStatus.IN_PROGRESS
            ]))
            .order_by(Trip.requested_at.desc())
        )
        result = await self.session.exec(stmt)
        return result.first()

    async def get_active_for_driver(self, driver_id: uuid.UUID) -> Optional[Trip]:
        """Return the current active trip assigned to a driver."""
        stmt = (
            select(Trip)
            .where(Trip.driver_id == driver_id)
            .where(Trip.status.in_([
                TripStatus.ACTIVE, TripStatus.EN_ROUTE,
                TripStatus.ARRIVED, TripStatus.AWAITING_CONFIRMATION,
                TripStatus.IN_PROGRESS
            ]))
        )
        result = await self.session.exec(stmt)
        return result.first()

    async def get_pending_for_driver(self, driver_id: uuid.UUID) -> Optional[Trip]:
        """Return a PENDING trip that has been assigned to this driver but not yet accepted."""
        stmt = (
            select(Trip)
            .where(Trip.driver_id == driver_id)
            .where(Trip.status == TripStatus.PENDING)
        )
        result = await self.session.exec(stmt)
        return result.first()

    async def get_trips_for_rider(self, rider_id: uuid.UUID, limit: int = 20) -> list[Trip]:
        """Full trip history for a rider, newest first."""
        stmt = (
            select(Trip)
            .where(Trip.rider_id == rider_id)
            .order_by(Trip.requested_at.desc())
            .limit(limit)
        )
        result = await self.session.exec(stmt)
        return list(result.all())

    async def get_trips_for_driver(self, driver_id: uuid.UUID, limit: int = 20) -> list[Trip]:
        """Full trip history for a driver, newest first."""
        stmt = (
            select(Trip)
            .where(Trip.driver_id == driver_id)
            .order_by(Trip.requested_at.desc())
            .limit(limit)
        )
        result = await self.session.exec(stmt)
        return list(result.all())

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    async def update(self, trip: Trip) -> Trip:
        self.session.add(trip)
        await self.session.commit()
        await self.session.refresh(trip)
        return trip
