import pytest
import uuid
import os
from httpx import AsyncClient
from app.main import app
from app.core.security import get_access_token
from app.db.session import engine
from app.repositories.user_repo import create_user
from app.schemas.user import UserCreate
from app.models.driving import DriverProfile, Trip, TripStatus, DriverRank, DriverStatus
from app.models.portfolio import UserPortfolio, Review
from app.models.profile import Profile
from sqlalchemy import select
from sqlmodel.ext.asyncio.session import AsyncSession

@pytest.mark.asyncio
async def test_driver_reviews_and_profile():
    # Setup database session
    async with AsyncSession(engine, expire_on_commit=False) as db:
        # 1. Create a Driver User
        driver_email = f"driver_{uuid.uuid4().hex[:8]}@example.com"
        driver_username = f"driver_{uuid.uuid4().hex[:8]}"
        driver_user = await create_user(db, UserCreate(email=driver_email, username=driver_username, password="password123", referral_code=None), password="hashed")

        # Create profile for driver (so they have first/last name)
        driver_profile_record = Profile(user_id=driver_user.id, first_name="Speedy", last_name="McQueen", country="Nigeria")
        db.add(driver_profile_record)

        # Create DriverProfile
        driver_profile = DriverProfile(
            user_id=driver_user.id,
            car_name="Tesla",
            car_model="Model S",
            plate_number="FAST-123",
            status=DriverStatus.ACTIVE,
            rank=DriverRank.STARTER
        )
        db.add(driver_profile)
        await db.commit()
        await db.refresh(driver_profile)

        # 2. Create a Rider User
        rider_email = f"rider_{uuid.uuid4().hex[:8]}@example.com"
        rider_username = f"rider_{uuid.uuid4().hex[:8]}"
        rider_user = await create_user(db, UserCreate(email=rider_email, username=rider_username, password="password123", referral_code=None), password="hashed")
        rider_token = await get_access_token(str(rider_user.id))

        # 3. Create a Completed Trip
        trip = Trip(
            rider_id=rider_user.id,
            driver_id=driver_profile.id,
            pickup_lat=6.5244,
            pickup_lng=3.3792,
            dropoff_lat=6.6018,
            dropoff_lng=3.3515,
            pickup_address="Lagos",
            dropoff_address="Ikeja",
            distance_km=10.0,
            estimated_fare=2000.0,
            final_fare=2000.0,
            surge_multiplier=1.0,
            status=TripStatus.COMPLETED
        )
        db.add(trip)
        await db.commit()
        await db.refresh(trip)

        # 4. Submit a review for the trip
        headers = {
            "Authorization": f"Bearer {rider_token}",
            "X-API-KEY": os.getenv("API_KEY", ""),
        }
        
        async with AsyncClient(app=app, base_url="http://test") as ac:
            review_payload = {
                "rating": 5,
                "comment": "Incredible experience, super clean car!"
            }
            res_review = await ac.post(f"/drivers/trips/{trip.id}/review", json=review_payload, headers=headers)
            assert res_review.status_code == 201, f"Expected 201, got {res_review.status_code}: {res_review.text}"
            
            # Verify review exists in DB
            res_data = res_review.json()
            assert res_data["status"] == "success"
            
            # 5. Fetch Public Driver Profile
            res_profile = await ac.get(f"/drivers/{driver_profile.id}/public-profile", headers=headers)
            assert res_profile.status_code == 200, f"Expected 200, got {res_profile.status_code}: {res_profile.text}"
            
            profile_data = res_profile.json()
            assert profile_data["driver_name"] == "Speedy McQueen"
            assert profile_data["car_name"] == "Tesla"
            assert len(profile_data["reviews"]) == 1
            assert profile_data["reviews"][0]["rating"] == 5
            assert profile_data["reviews"][0]["comment"] == "Incredible experience, super clean car!"
            assert profile_data["reviews"][0]["reviewer_name"] == rider_username
            
            assert len(profile_data["completed_trips"]) == 1
            assert profile_data["completed_trips"][0]["pickup_address"] == "Lagos"
            assert profile_data["completed_trips"][0]["dropoff_address"] == "Ikeja"
            assert profile_data["successful_rides"] == 1
            assert profile_data["total_rides"] == 1

        # 6. Cleanup DB records
        # Fetch portfolio
        port_res = await db.execute(select(UserPortfolio).where(UserPortfolio.user_id == driver_user.id))
        portfolio = port_res.scalars().first()
        if portfolio:
            revs_res = await db.execute(select(Review).where(Review.portfolio_id == portfolio.id))
            for r in revs_res.scalars().all():
                await db.delete(r)
            await db.delete(portfolio)
        
        await db.delete(trip)
        await db.delete(driver_profile)
        await db.delete(driver_profile_record)
        await db.delete(driver_user)
        await db.delete(rider_user)
        await db.commit()


@pytest.mark.asyncio
async def test_driver_negotiation():
    # Setup database session
    async with AsyncSession(engine, expire_on_commit=False) as db:
        # 1. Create a Driver User
        driver_email = f"driver_{uuid.uuid4().hex[:8]}@example.com"
        driver_username = f"driver_{uuid.uuid4().hex[:8]}"
        driver_user = await create_user(db, UserCreate(email=driver_email, username=driver_username, password="password123", referral_code=None), password="hashed")
        driver_token = await get_access_token(str(driver_user.id))

        # Create DriverProfile
        driver_profile = DriverProfile(
            user_id=driver_user.id,
            car_name="Tesla",
            car_model="Model S",
            plate_number="FAST-123",
            status=DriverStatus.ACTIVE,
            rank=DriverRank.STARTER
        )
        db.add(driver_profile)
        
        # 2. Create a Rider User
        rider_email = f"rider_{uuid.uuid4().hex[:8]}@example.com"
        rider_username = f"rider_{uuid.uuid4().hex[:8]}"
        rider_user = await create_user(db, UserCreate(email=rider_email, username=rider_username, password="password123", referral_code=None), password="hashed")
        rider_token = await get_access_token(str(rider_user.id))
        
        await db.commit()
        await db.refresh(driver_profile)

        # Set driver available in redis so request_ride doesn't fail
        from app.dependencies.socket_connection import manager
        await manager.start()
        from app.services.redis_location import RedisLocationService
        redis_loc = RedisLocationService(manager._redis)
        await redis_loc.set_availability(driver_profile.id, available=True)
        # Ping location so driver has lat/lng
        await redis_loc.update_location(driver_profile.id, 6.5244, 3.3792)

        rider_headers = {
            "Authorization": f"Bearer {rider_token}",
            "X-API-KEY": os.getenv("API_KEY", ""),
        }
        driver_headers = {
            "Authorization": f"Bearer {driver_token}",
            "X-API-KEY": os.getenv("API_KEY", ""),
        }
        
        async with AsyncClient(app=app, base_url="http://test") as ac:
            # 3. Rider requests ride with negotiation
            request_payload = {
                "pickup_lat": 6.5244,
                "pickup_lng": 3.3792,
                "dropoff_lat": 6.6018,
                "dropoff_lng": 3.3515,
                "pickup_address": "Lagos",
                "dropoff_address": "Ikeja",
                "surge_multiplier": 1.0,
                "driver_id": str(driver_profile.id),
                "negotiated_fare": 1500.0,
            }
            res_req = await ac.post("/drivers/trips/request", json=request_payload, headers=rider_headers)
            assert res_req.status_code == 201, f"Expected 201, got {res_req.status_code}: {res_req.text}"
            
            trip_data = res_req.json()
            trip_id = trip_data["id"]
            assert trip_data["negotiated_fare"] == 1500.0
            assert trip_data["status"] == "pending"

            # 4. Driver proposes counter offer
            counter_payload = {
                "counter_fare": 1800.0
            }
            res_counter = await ac.post(f"/drivers/trips/{trip_id}/counter", json=counter_payload, headers=driver_headers)
            assert res_counter.status_code == 200, f"Expected 200, got {res_counter.status_code}: {res_counter.text}"
            
            counter_data = res_counter.json()
            assert counter_data["negotiated_fare"] == 1800.0
            assert counter_data["status"] == "pending"

            # 5. Rider accepts counter offer
            res_accept = await ac.post(f"/drivers/trips/{trip_id}/accept_counter", headers=rider_headers)
            assert res_accept.status_code == 200, f"Expected 200, got {res_accept.status_code}: {res_accept.text}"
            
            accept_data = res_accept.json()
            assert accept_data["estimated_fare"] == 1800.0
            assert accept_data["status"] == "en_route"

        # 6. Cleanup DB records
        from app.models.notifications import Notification
        notifs_res = await db.execute(select(Notification).where(
            (Notification.user_id == driver_user.id) | (Notification.actor_id == rider_user.id)
        ))
        for n in notifs_res.scalars().all():
            await db.delete(n)

        db_trip = await db.get(Trip, uuid.UUID(trip_id))
        if db_trip:
            await db.delete(db_trip)
        await db.delete(driver_profile)
        await db.delete(driver_user)
        await db.delete(rider_user)
        await db.commit()
        await manager.stop()
