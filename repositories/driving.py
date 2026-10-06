import uuid
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from app.models.driving import DriverProfile, Ride, RideStatus, DriverLocation, DriverStatus
from sqlalchemy import func, text


class DriverRepository:
    """

    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, driver: DriverProfile) -> DriverProfile:
        self.session.add(driver)
        await self.session.commit()
        await self.session.refresh(driver)
        return driver

    async def get_by_user_id(self, user_id: uuid.UUID) -> DriverProfile | None:
        statement = select(DriverProfile).where(DriverProfile.user_id == user_id)
        result = await self.session.exec(statement)
        return result.first()

    async def get_by_id(self, driver_id: uuid.UUID) -> DriverProfile | None:
        statement = select(DriverProfile).where(DriverProfile.id == driver_id)
        result = await self.session.exec(statement)
        return result.first()

    async def update(self, driver: DriverProfile) -> DriverProfile:
        self.session.add(driver)
        await self.session.commit()
        await self.session.refresh(driver)
        return driver


class RideRepository:
    """

    """
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, ride: Ride) -> Ride:
        self.session.add(ride)
        await self.session.commit()
        await self.session.refresh(ride)
        return ride

    async def get_by_id(self, ride_id: uuid.UUID) -> Ride | None:
        return await self.session.get(Ride, ride_id)

    async def get_active_ride(self, driver_id: uuid.UUID) -> Ride | None:
        statement = select(Ride).where(
            Ride.driver_id == driver_id,
            Ride.status == RideStatus.STARTED
        )
        result = await self.session.exec(statement)
        return result.first()

    async def update(self, ride: Ride) -> Ride:
        self.session.add(ride)
        await self.session.commit()
        await self.session.refresh(ride)
        return ride



class LocationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert_location(self, driver_id: uuid.UUID, lat: float, lon: float):
        """
        Insert location if new, update if exists.
        """
        loc = await self.session.get(DriverLocation, driver_id)

        if loc:
            loc.latitude = lat
            loc.longitude = lon
        else:
            loc = DriverLocation(driver_id=driver_id, latitude=lat, longitude=lon)
            self.session.add(loc)

        await self.session.commit()
        await self.session.refresh(loc)
        return loc

    async def get_nearby_drivers(self, user_lat: float, user_lon: float, radius_km: float):
        """
        Finds active drivers within radius_km using the Haversine formula.
        Returns tuples: (DriverLocation, DriverProfile, distance_km)
        """
        # 6371 is Earth's radius in KM
        # Formula: acos(sin(lat)*sin(d_lat) + cos(lat)*cos(d_lat)*cos(d_lon - lon)) * 6371

        # Note: In production with millions of rows, use PostGIS.
        # For now, this SQL math is fine.

        distance_expression = (
                6371 * func.acos(
            func.cos(func.radians(user_lat)) * func.cos(func.radians(DriverLocation.latitude)) * func.cos(
                func.radians(DriverLocation.longitude) - func.radians(user_lon)) +
            func.sin(func.radians(user_lat)) * func.sin(func.radians(DriverLocation.latitude))
        )
        )

        statement = (
            select(DriverLocation, DriverProfile, distance_expression.label("distance"))
            .join(DriverProfile, DriverLocation.driver_id == DriverProfile.id)
            .where(DriverProfile.status == DriverStatus.ACTIVE)  # Only active drivers
            .where(distance_expression <= radius_km)
            .order_by("distance")
        )

        results = await self.session.exec(statement)
        return results.all()