import uuid
from datetime import datetime, timezone
from typing import List
from app.repositories.driving import DriverRepository, RideRepository,LocationRepository
from app.schemas.driving import DriverCreate, DriverUpdate, RideCreate, RideComplete, DriverNearbyResponse, \
    LocationUpdate
from app.models.driving import DriverProfile, Ride, RideStatus, DriverRank
from app.schemas.user import UserRead


class DriverService:
    """

    """
    def __init__(self, session):
        self.repo = DriverRepository(session)

    async def create_driver_profile(self, user: UserRead, payload: DriverCreate) -> DriverProfile:
        """

        :param user:
        :param payload:
        :return:
        """
        from app.models.kyc import KYC, KYCStatus
        from sqlmodel import select

        # Enforce KYC verification
        stmt = select(KYC).where(KYC.user_id == user.id)
        res = await self.repo.session.execute(stmt)
        kyc = res.scalar_one_or_none()

        if not kyc or kyc.status != KYCStatus.verified:
            raise ValueError("User ID verification must be completed first.")

        existing_profile = await self.repo.get_by_user_id(user.id)
        if existing_profile:
            raise ValueError("User already has a driver profile.")

        license_number = getattr(payload, "license_number", None)
        license_picture_url = getattr(payload, "license_picture_url", None)
        license_status = "pending" if (license_number and license_picture_url) else "unverified"

        new_driver = DriverProfile(
            user_id=user.id,
            car_name=payload.car_name,
            car_model=payload.car_model,
            plate_number=payload.plate_number,
            vehicle_type=payload.vehicle_type or "car",
            car_picture_url=payload.car_picture_url,
            license_number=license_number,
            license_picture_url=license_picture_url,
            license_status=license_status,
        )

        return await self.repo.create(new_driver)

    async def get_driver_profile(self, user_id: uuid.UUID) -> DriverProfile:
        """

        :param user_id:
        :return:
        """
        profile = await self.repo.get_by_user_id(user_id)
        if not profile:
            raise ValueError("Driver profile not found")
        return profile

    async def get_driver_profile_by_id(self, driver_id: uuid.UUID) -> DriverProfile:
        """

        :param driver_id:
        :return:
        """
        profile = await self.repo.get_by_id(driver_id)
        if not profile:
            raise ValueError("Driver profile not found")
        return profile


    async def update_driver_profile(self, user: UserRead, payload: DriverUpdate) -> DriverProfile:
        """

        :param user:
        :param payload:
        :return:
        """
        current_profile = await self.repo.get_by_user_id(user.id)
        if not current_profile:
            raise ValueError("Driver profile not found")

        if current_profile.user_id != user.id:
            raise PermissionError("You cannot update another user's profile")

        update_data = payload.model_dump(exclude_unset=True)
        
        # Update license status if license fields are being changed
        if "license_number" in update_data or "license_picture_url" in update_data:
            val_number = update_data.get("license_number", current_profile.license_number)
            val_pic = update_data.get("license_picture_url", current_profile.license_picture_url)
            if val_number and val_pic:
                current_profile.license_status = "pending"
                current_profile.license_rejection_reason = None

        for key, value in update_data.items():
            setattr(current_profile, key, value)

        return await self.repo.update(current_profile)



RANK_THRESHOLDS = {
    DriverRank.LEGEND: 500,
    DriverRank.EXPERT: 100,
    DriverRank.EXPERIENCED: 20,
}



class RideService:
    """

    """

    def __init__(self, session):
        self.ride_repo = RideRepository(session)
        self.driver_repo = DriverRepository(session)

    async def start_ride(self, user: UserRead, payload: RideCreate) -> Ride:
        # 1. Get Driver Profile
        driver_profile = await self.driver_repo.get_by_user_id(user.id)
        if not driver_profile:
            raise ValueError("You must create a driver profile before driving.")

        active_ride = await self.ride_repo.get_active_ride(driver_profile.id)
        if active_ride:
            raise ValueError("You already have a ride in progress.")

        new_ride = Ride(
            driver_id=driver_profile.id,
            user_id=user.id,
            start_location=payload.start_location,
            destination=payload.destination,
            status=RideStatus.STARTED
        )
        return await self.ride_repo.create(new_ride)

    async def complete_ride(self, user: UserRead, ride_id: uuid.UUID, payload: RideComplete) -> Ride:
        """

        :param user:
        :param ride_id:
        :param payload:
        :return:
        """
        ride = await self.ride_repo.get_by_id(ride_id)
        if not ride:
            raise ValueError("Ride not found.")

        if ride.user_id != user.id:
            raise PermissionError("Not your ride.")

        if ride.status != RideStatus.STARTED:
            raise ValueError("Ride is already finished.")

        ride.end_time = datetime.now(timezone.utc)
        ride.earnings = payload.earnings

        if payload.success:
            ride.status = RideStatus.COMPLETED
        else:
            ride.status = RideStatus.FAILED

        await self._update_driver_stats(ride.driver_id, payload.success)

        return await self.ride_repo.update(ride)

    async def _update_driver_stats(self, driver_id: uuid.UUID, is_success: bool):
        """
        Internal helper to increment counters and handle Rank Upgrades.
        """
        profile = await self.driver_repo.get_by_id(driver_id)

        profile.total_rides += 1
        if is_success:
            profile.successful_rides += 1
            await self._check_rank_upgrade(profile)
        else:
            profile.failed_rides += 1

        await self.driver_repo.update(profile)

    async def _check_rank_upgrade(self, profile):
        """Logic to upgrade rank based on success count"""
        current_rank = profile.rank
        success_count = profile.successful_rides

        for rank, threshold in RANK_THRESHOLDS.items():
            if success_count >= threshold:
                if current_rank != rank:
                    profile.rank = rank
                break




class LocationService:
    """

    """
    def __init__(self, session):
        self.repo = LocationRepository(session)

    async def update_driver_location(self, driver_id: uuid.UUID, payload: LocationUpdate):
        """

        :param driver_id:
        :param payload:
        :return:
        """
        return await self.repo.upsert_location(
            driver_id,
            payload.latitude,
            payload.longitude
        )

    async def find_nearby_drivers(self, lat: float, lon: float, radius: float) -> List[DriverNearbyResponse]:
        """

        :param lat:
        :param lon:
        :param radius:
        :return:
        """
        raw_results = await self.repo.get_nearby_drivers(lat, lon, radius)

        response_list = []
        for location, profile, distance in raw_results:
            response_list.append(
                DriverNearbyResponse(
                    driver_id=profile.id,
                    latitude=location.latitude,
                    longitude=location.longitude,
                    distance_km=round(distance, 2),
                    car_name=f"{profile.car_name} {profile.car_model}"
                )
            )
        return response_list
