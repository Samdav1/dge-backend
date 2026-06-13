"""
matching_service.py
-------------------
The "brain" of the driving system.

Orchestration flow when a rider requests a ride:
  1. Query Redis GEO for the closest available drivers within radius_km.
  2. Fetch the top driver's profile from PostgreSQL (name, car, plate).
  3. Calculate the estimated fare via the Pricing Engine.
  4. Persist a Trip record in PostgreSQL (status=PENDING).
  5. Mark the driver as unavailable in Redis.
  6. Push a WebSocket notification to the driver.
  7. Schedule a 30-second timeout task — if the driver doesn't accept,
     flip the trip to CANCELLED and notify the rider.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.driving import Trip, TripStatus, DriverProfile
from app.repositories.driving import DriverRepository, LocationRepository
from app.repositories.trip_repo import TripRepository
from app.services.redis_location import RedisLocationService
from app.services.pricing_service import calculate_trip_fare

logger = logging.getLogger(__name__)

ACCEPT_TIMEOUT_SECONDS = 30  # How long driver has to accept before the request is cancelled


class MatchingService:
    """
    Stateless service — instantiated per-request via FastAPI dependency injection.
    The ConnectionManager (for WebSocket pushes) is injected because it's a
    singleton held by the app; we receive it from the caller.
    """

    def __init__(
        self,
        session: AsyncSession,
        redis_location: RedisLocationService,
        connection_manager,          # app.dependencies.socket_connection.ConnectionManager
    ):
        self.session = session
        self.redis_loc = redis_location
        self.manager = connection_manager
        self.trip_repo = TripRepository(session)
        self.driver_repo = DriverRepository(session)
        self.loc_repo = LocationRepository(session)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def request_ride(
        self,
        rider_id: uuid.UUID,
        pickup_lat: float,
        pickup_lng: float,
        dropoff_lat: float,
        dropoff_lng: float,
        pickup_address: Optional[str] = None,
        dropoff_address: Optional[str] = None,
        surge_multiplier: float = 1.0,
        radius_km: float = 5.0,
        driver_id: Optional[uuid.UUID] = None,
        negotiated_fare: Optional[float] = None,
    ) -> Trip:
        """
        Entry point called by POST /drivers/trips/request.
        Returns the newly created Trip.

        Raises:
            ValueError — no available drivers found within radius.
        """
        # 1. Guard: rider must not already have a pending/active trip
        existing = await self.trip_repo.get_active_for_rider(rider_id)
        if existing:
            raise ValueError(
                f"You already have an active trip ({existing.id}). "
                "Cancel it before requesting a new one."
            )

        # 2. Find driver (either nearest or specifically selected)
        if driver_id:
            # Direct negotiation request
            driver_uuid = driver_id
            
            # 1. Check if driver is already busy
            active_trip = await self.trip_repo.get_active_for_driver(driver_uuid)
            if active_trip:
                raise ValueError("This driver is currently on another ride. Please choose a different driver.")
                
            pending_trip = await self.trip_repo.get_pending_for_driver(driver_uuid)
            if pending_trip:
                raise ValueError("This driver is currently considering another ride request. Please try again later.")

            distance_to_driver_km = 0.0 # Could fetch from Redis to be accurate
            
            # 2. Verify driver is available in Redis
            avail_raw = await self.redis_loc._r.get(f"driver:avail:{str(driver_uuid)}")
            is_avail = avail_raw and (avail_raw.decode() if isinstance(avail_raw, bytes) else str(avail_raw)) == "1"
            if not is_avail:
                raise ValueError("Selected driver is currently unavailable.")
        else:
            # Find nearest available driver via Redis GEO
            nearby = await self.redis_loc.find_nearby_available(
                lat=pickup_lat,
                lng=pickup_lng,
                radius_km=radius_km,
            )
            if not nearby:
                raise ValueError(
                    f"No available drivers found within {radius_km} km. "
                    "Please try again in a moment."
                )

            # Pick the single closest driver
            closest = nearby[0]
            driver_uuid = uuid.UUID(closest["driver_id"])
            distance_to_driver_km = closest["distance_km"]

        # 3. Fetch driver's PostgreSQL profile for notification payload
        driver_profile: Optional[DriverProfile] = await self.driver_repo.get_by_id(driver_uuid)
        if not driver_profile:
            raise ValueError("Matched driver profile not found in database.")

        # 4. Pricing engine
        if negotiated_fare is not None:
            # Direct negotiation overrides calculated fare
            fare_obj = calculate_trip_fare(
                pickup_lat=pickup_lat,
                pickup_lng=pickup_lng,
                dropoff_lat=dropoff_lat,
                dropoff_lng=dropoff_lng,
            )
            fare_obj.estimated_fare = negotiated_fare
            fare = fare_obj
        else:
            fare = calculate_trip_fare(
                pickup_lat=pickup_lat,
                pickup_lng=pickup_lng,
                dropoff_lat=dropoff_lat,
                dropoff_lng=dropoff_lng,
                surge_multiplier=surge_multiplier,
            )

        # 5. Persist Trip record (PENDING — no driver linked yet until acceptance)
        trip = Trip(
            rider_id=rider_id,
            driver_id=driver_uuid,          # tentatively assigned; confirmed on accept
            pickup_lat=pickup_lat,
            pickup_lng=pickup_lng,
            dropoff_lat=dropoff_lat,
            dropoff_lng=dropoff_lng,
            pickup_address=pickup_address,
            dropoff_address=dropoff_address,
            distance_km=fare.distance_km,
            estimated_fare=fare.estimated_fare,
            surge_multiplier=surge_multiplier,
            status=TripStatus.PENDING,
        )
        trip = await self.trip_repo.create(trip)

        # 6. Mark driver as unavailable in Redis so they don't get double-matched
        await self.redis_loc.set_availability(driver_uuid, available=False)

        # 7. Push ride_request notification to driver via WebSocket
        await self._notify_driver(driver_profile, trip, fare, distance_to_driver_km)

        # 8. Schedule acceptance timeout in background
        asyncio.create_task(self._acceptance_timeout(trip.id, driver_uuid, str(rider_id)))

        logger.info(
            "Trip %s created | rider=%s | driver=%s | fare=%.2f",
            trip.id, rider_id, driver_uuid, fare.estimated_fare,
        )
        return trip

    async def broadcast_ride_intent(
        self,
        rider_id: uuid.UUID,
        pickup_lat: float,
        pickup_lng: float,
        dropoff_lat: float,
        dropoff_lng: float,
        pickup_address: Optional[str] = None,
        dropoff_address: Optional[str] = None,
        radius_km: float = 5.0,
    ) -> dict:
        """
        Find nearby drivers and push an 'incoming_ride_intent' WebSocket event to them.
        Returns the number of drivers notified.
        """
        nearby = await self.redis_loc.find_nearby_available(
            lat=pickup_lat,
            lng=pickup_lng,
            radius_km=radius_km,
        )
        
        if not nearby:
            return {"notified": 0}

        fare = calculate_trip_fare(
            pickup_lat=pickup_lat,
            pickup_lng=pickup_lng,
            dropoff_lat=dropoff_lat,
            dropoff_lng=dropoff_lng,
        )

        notified_count = 0
        for driver in nearby:
            driver_uuid = uuid.UUID(driver["driver_id"])
            distance_to_driver_km = driver["distance_km"]
            
            driver_profile = await self.driver_repo.get_by_id(driver_uuid)
            if not driver_profile:
                continue

            payload = {
                "type": "incoming_ride_intent",
                "rider_id": str(rider_id),
                "pickup": {
                    "lat": pickup_lat,
                    "lng": pickup_lng,
                    "address": pickup_address or "",
                },
                "dropoff": {
                    "lat": dropoff_lat,
                    "lng": dropoff_lng,
                    "address": dropoff_address or "",
                },
                "distance_km": fare.distance_km,
                "estimated_fare": fare.estimated_fare,
                "distance_to_pickup_km": distance_to_driver_km,
            }
            await self.manager.send_to_user(str(driver_profile.user_id), payload)
            notified_count += 1
            
        # Also broadcast globally for drivers who selected "Country-Wide"
        global_payload = {
            "type": "incoming_ride_intent",
            "rider_id": str(rider_id),
            "pickup": {
                "lat": pickup_lat,
                "lng": pickup_lng,
                "address": pickup_address or "",
            },
            "dropoff": {
                "lat": dropoff_lat,
                "lng": dropoff_lng,
                "address": dropoff_address or "",
            },
            "distance_km": fare.distance_km,
            "estimated_fare": fare.estimated_fare,
            "distance_to_pickup_km": 0, # Cannot compute accurate distance without driver location
            "is_global": True,
        }
        await self.manager.broadcast_conversation("driving_requests_global", global_payload)
            
        return {"notified": notified_count}

    async def accept_trip(self, driver_id: uuid.UUID, trip_id: uuid.UUID) -> Trip:
        """
        Called by POST /drivers/trips/{trip_id}/accept.
        Transitions trip PENDING → ACTIVE and notifies the rider.
        """
        trip = await self.trip_repo.get_by_id(trip_id)
        if not trip:
            raise ValueError("Trip not found.")
        if trip.driver_id != driver_id:
            raise PermissionError("This trip is not assigned to you.")
        if trip.status != TripStatus.PENDING:
            raise ValueError(f"Trip cannot be accepted — current status: {trip.status}")

        trip.status = TripStatus.EN_ROUTE
        trip.accepted_at = datetime.now(timezone.utc)
        trip = await self.trip_repo.update(trip)

        # Fetch driver profile to send name/car to rider
        driver_profile = await self.driver_repo.get_by_id(driver_id)

        # Notify rider via WebSocket
        await self.manager.send_to_user(
            str(trip.rider_id),
            {
                "type": "ride_accepted",
                "trip_id": str(trip.id),
                "driver": {
                    "driver_id": str(driver_id),
                    "car": f"{driver_profile.car_name} {driver_profile.car_model}"
                    if driver_profile else "Unknown",
                    "plate": driver_profile.plate_number if driver_profile else "",
                },
            },
        )
        await self._publish_to_ride_channel(trip.id, {"type": "ride_accepted", "trip_id": str(trip.id)})

        logger.info("Trip %s accepted by driver %s (EN_ROUTE)", trip_id, driver_id)
        return trip

    async def arrive_at_pickup(self, driver_id: uuid.UUID, trip_id: uuid.UUID) -> Trip:
        trip = await self.trip_repo.get_by_id(trip_id)
        if not trip:
            raise ValueError("Trip not found.")
        if trip.driver_id != driver_id:
            raise PermissionError("This trip is not assigned to you.")
        if trip.status != TripStatus.EN_ROUTE and trip.status != TripStatus.ACTIVE:
            raise ValueError(f"Driver hasn't accepted trip or already arrived — current: {trip.status}")

        trip.status = TripStatus.ARRIVED
        trip = await self.trip_repo.update(trip)

        payload = {"type": "driver_arrived", "trip_id": str(trip.id)}
        await self.manager.send_to_user(str(trip.rider_id), payload)
        await self._publish_to_ride_channel(trip.id, payload)

        logger.info("Driver %s arrived for trip %s", driver_id, trip_id)
        return trip

    async def start_trip(self, driver_id: uuid.UUID, trip_id: uuid.UUID) -> Trip:
        trip = await self.trip_repo.get_by_id(trip_id)
        if not trip:
            raise ValueError("Trip not found.")
        if trip.driver_id != driver_id:
            raise PermissionError("This trip is not assigned to you.")
        if trip.status != TripStatus.ARRIVED:
            raise ValueError(f"Must arrive before starting trip — current: {trip.status}")

        trip.status = TripStatus.AWAITING_CONFIRMATION
        trip = await self.trip_repo.update(trip)

        payload = {"type": "trip_start_requested", "trip_id": str(trip.id)}
        await self.manager.send_to_user(str(trip.rider_id), payload)
        await self._publish_to_ride_channel(trip.id, payload)

        logger.info("Driver %s requested trip start for %s", driver_id, trip_id)
        return trip

    async def confirm_start(self, rider_id: uuid.UUID, trip_id: uuid.UUID) -> Trip:
        trip = await self.trip_repo.get_by_id(trip_id)
        if not trip:
            raise ValueError("Trip not found.")
        if trip.rider_id != rider_id:
            raise PermissionError("This trip does not belong to you.")
        if trip.status != TripStatus.AWAITING_CONFIRMATION:
            raise ValueError(f"Cannot confirm start — current: {trip.status}")

        trip.status = TripStatus.IN_PROGRESS
        trip = await self.trip_repo.update(trip)

        payload = {"type": "trip_started", "trip_id": str(trip.id)}
        if trip.driver_id:
            from app.repositories.driving import DriverRepository
            driver_repo = DriverRepository(self.session)
            driver = await driver_repo.get_by_id(trip.driver_id)
            if driver:
                await self.manager.send_to_user(str(driver.user_id), payload)
        await self._publish_to_ride_channel(trip.id, payload)

        logger.info("Rider %s confirmed trip start for %s", rider_id, trip_id)
        return trip

    async def cancel_trip(
        self,
        trip_id: uuid.UUID,
        cancelled_by_id: uuid.UUID,
        reason: Optional[str] = None,
    ) -> Trip:
        """Cancel a PENDING or ACTIVE trip. Called by rider or driver."""
        trip = await self.trip_repo.get_by_id(trip_id)
        if not trip:
            raise ValueError("Trip not found.")
        if trip.status in (TripStatus.COMPLETED, TripStatus.CANCELLED):
            raise ValueError(f"Trip already in terminal state: {trip.status}")
        if trip.rider_id != cancelled_by_id and trip.driver_id != cancelled_by_id:
            raise PermissionError("You are not a party to this trip.")

        trip.status = TripStatus.CANCELLED
        trip = await self.trip_repo.update(trip)

        # Re-enable driver availability
        if trip.driver_id:
            await self.redis_loc.set_availability(trip.driver_id, available=True)

        # Broadcast cancellation to both parties
        payload = {
            "type": "ride_cancelled",
            "trip_id": str(trip.id),
            "cancelled_by": str(cancelled_by_id),
            "reason": reason or "",
        }
        await self.manager.send_to_user(str(trip.rider_id), payload)
        if trip.driver_id:
            from app.repositories.driving import DriverRepository
            driver_repo = DriverRepository(self.session)
            driver = await driver_repo.get_by_id(trip.driver_id)
            if driver:
                await self.manager.send_to_user(str(driver.user_id), payload)
        await self._publish_to_ride_channel(trip.id, payload)

        # Trigger cancellation email
        try:
            from app.services.email_notification_service import NotificationService
            from app.repositories.user_repo import get_user_by_id
            
            rider_user = await get_user_by_id(db=self.session, user_id=trip.rider_id)
            driver_user = None
            if trip.driver_id:
                driver_profile = await DriverRepository(self.session).get_by_id(trip.driver_id)
                if driver_profile:
                    driver_user = await get_user_by_id(db=self.session, user_id=driver_profile.user_id)
            
            cancelled_by_user = rider_user if cancelled_by_id == trip.rider_id else driver_user
            
            if rider_user and cancelled_by_user:
                NotificationService().send_ride_cancelled_mail(
                    rider=rider_user, 
                    driver=driver_user, 
                    cancelled_by=cancelled_by_user
                )
        except Exception as e:
            logger.error(f"Failed to send cancellation email for trip {trip.id}: {e}")

        logger.info("Trip %s cancelled by %s", trip_id, cancelled_by_id)
        return trip

    async def complete_trip(
        self,
        driver_id: uuid.UUID,
        trip_id: uuid.UUID,
        final_fare: Optional[float] = None,
    ) -> Trip:
        """Driver marks the trip as COMPLETED. Triggers driver stat update."""
        trip = await self.trip_repo.get_by_id(trip_id)
        if not trip:
            raise ValueError("Trip not found.")
        if trip.driver_id != driver_id:
            raise PermissionError("This trip is not yours.")
        if trip.status not in (TripStatus.IN_PROGRESS, TripStatus.ACTIVE):
            raise ValueError(f"Trip must be IN_PROGRESS to complete — current: {trip.status}")

        trip.status = TripStatus.COMPLETED
        trip.completed_at = datetime.now(timezone.utc)
        trip.final_fare = final_fare if final_fare is not None else trip.estimated_fare
        
        # 1. Process Wallet Deductions & Credits
        from app.repositories.wallet_repo import update_user_wallet_balance_repo_ext
        from app.models.wallet import WalletType
        from app.services.fee_service import fee_service
        from app.repositories.transactions_repo import TransactionRepository
        from app.schemas.transactions import TransactionCreate
        from app.models.transactions import TxnType, TxnStatus
        
        # Deduct from rider (using deposit wallet)
        # Note: This will raise HTTPException(400) if balance < 0
        fare_cents = int(trip.final_fare * 100)
        try:
            rider_wallet = await update_user_wallet_balance_repo_ext(
                db=self.session, 
                credentials=trip.rider_id, 
                amount=-fare_cents, 
                wallet_type=WalletType.deposit,
                allow_negative=True
            )
            
            # 2. Calculate platform fee
            # Use the fee_service. Let's use event_type="payment" or "escrow_release" as a proxy, 
            # or just calculate manually if we want a default 10% fee. We'll use 10% for now.
            fee_cents = int(fare_cents * 0.10)
            net_cents = fare_cents - fee_cents
            
            # 3. Credit driver (using earnings wallet)
            from app.repositories.driving import DriverRepository
            driver_user_id = (await DriverRepository(self.session).get_by_id(trip.driver_id)).user_id
            driver_wallet = await update_user_wallet_balance_repo_ext(
                db=self.session, 
                credentials=driver_user_id, 
                amount=net_cents, 
                wallet_type=WalletType.earnings
            )
            
            # 4. Create Transaction Records
            txn_repo = TransactionRepository(self.session)
            
            # Rider Debit
            await txn_repo.create_transaction_ext(TransactionCreate(
                wallet_id=rider_wallet.id,
                users_id=trip.rider_id,
                type=TxnType.payment,
                amount_cents=fare_cents,
                status=TxnStatus.completed,
                reference=f"trip_pay_{trip.id}"
            ))
            
            # Driver Credit
            await txn_repo.create_transaction_ext(TransactionCreate(
                wallet_id=driver_wallet.id,
                users_id=driver_user_id,
                type=TxnType.payment,
                amount_cents=net_cents,
                status=TxnStatus.completed,
                reference=f"trip_earn_{trip.id}"
            ))
            
        except Exception as e:
            logger.error(f"Trip {trip.id} payment failed: {e}")
            raise ValueError(f"Payment failed: {e}")

        # Commit trip update and all wallet/transaction changes
        trip = await self.trip_repo.update(trip)

        # Re-enable driver availability
        await self.redis_loc.set_availability(driver_id, available=True)

        # Notify both parties
        payload = {
            "type": "ride_completed",
            "trip_id": str(trip.id),
            "final_fare": trip.final_fare,
        }
        await self.manager.send_to_user(str(trip.rider_id), payload)
        await self.manager.send_to_user(str(driver_id), payload)
        await self._publish_to_ride_channel(trip.id, payload)

        # Trigger completion email
        try:
            from app.services.email_notification_service import NotificationService
            from app.repositories.user_repo import get_user_by_id
            from app.repositories.driving import DriverRepository
            
            driver_user_id = (await DriverRepository(self.session).get_by_id(trip.driver_id)).user_id
            rider_user = await get_user_by_id(db=self.session, user_id=trip.rider_id)
            driver_user = await get_user_by_id(db=self.session, user_id=driver_user_id)
            
            if rider_user and driver_user:
                NotificationService().send_ride_completed_mail(
                    rider=rider_user, 
                    driver=driver_user, 
                    trip=trip
                )
        except Exception as e:
            logger.error(f"Failed to send completion email for trip {trip.id}: {e}")

        logger.info("Trip %s completed | final_fare=%.2f", trip_id, trip.final_fare)
        return trip

    async def handle_gps_ping(
        self,
        driver_id: uuid.UUID,
        lat: float,
        lng: float,
        is_available: bool = True,
        driver_details: Optional[dict] = None
    ) -> None:
        """
        Called by POST /drivers/ping.
        1. Write position to Redis (non-blocking).
        2. If driver has an ACTIVE trip, push location to rider via WebSocket.
        """
        # Always update Redis regardless of trip state
        await self.redis_loc.update_location(driver_id, lat, lng, available=is_available)

        # Broadcast live location to any riders browsing the map
        if is_available:
            payload = {
                "type": "driver_location",
                "driver_id": str(driver_id),
                "lat": lat,
                "lng": lng,
            }
            if driver_details:
                payload["details"] = driver_details
                
            await self.manager.broadcast_conversation("driving_global", payload)

        # Check for an active trip to forward location to rider
        active_trip = await self.trip_repo.get_active_for_driver(driver_id)
        if active_trip:
            payload = {
                "type": "location_update",
                "trip_id": str(active_trip.id),
                "lat": lat,
                "lng": lng,
            }
            # Push directly to rider's personal WS channel
            await self.manager.send_to_user(str(active_trip.rider_id), payload)
            # Also publish to the shared ride room
            await self._publish_to_ride_channel(active_trip.id, payload)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _notify_driver(self, driver_profile, trip: Trip, fare, distance_to_driver_km: float):
        """Push a ride_request event to the driver's WebSocket connection."""
        payload = {
            "type": "ride_request",
            "trip_id": str(trip.id),
            "rider_id": str(trip.rider_id),
            "pickup": {
                "lat": trip.pickup_lat,
                "lng": trip.pickup_lng,
                "address": trip.pickup_address or "",
            },
            "dropoff": {
                "lat": trip.dropoff_lat,
                "lng": trip.dropoff_lng,
                "address": trip.dropoff_address or "",
            },
            "distance_km": fare.distance_km,
            "estimated_fare": fare.estimated_fare,
            "distance_to_pickup_km": distance_to_driver_km,
            "expires_in_seconds": ACCEPT_TIMEOUT_SECONDS,
        }
        await self.manager.send_to_user(str(driver_profile.user_id), payload)

        # 1. Add DB notification for driver
        from app.repositories.notifications_repo import NotificationRepository
        from app.models.notifications import Notification, NotificationType
        notif_repo = NotificationRepository(self.session)
        new_notif = Notification(
            user_id=driver_profile.user_id,
            actor_id=trip.rider_id,
            type=NotificationType.general,
            message=f"You have a new ride request! Route: {trip.pickup_address[:15]}... to {trip.dropoff_address[:15]}...",
            metadataInfo={"trip_id": str(trip.id), "type": "ride_requested"}
        )
        await notif_repo.create(new_notif)

        # 2. Send Email notification
        try:
            from app.services.email_notification_service import NotificationService as EmailService
            from app.repositories.user_repo import get_user_by_id
            
            driver_user = await get_user_by_id(driver_profile.user_id, self.session)
            if driver_user:
                # Reuse the service_purchase template as a temporary fix for a ride request email
                email_svc = EmailService()
                rider_user = await get_user_by_id(trip.rider_id, self.session)
                if rider_user:
                    email_svc._render_and_dispatch(
                        'service_purchase.html', 
                        [str(driver_user.email)], 
                        "New Ride Request! 🚗", 
                        {
                            'is_buyer': False,
                            'name': driver_user.username,
                            'other_party': rider_user.username,
                            'service_title': f"Ride Request: {trip.pickup_address[:20]} to {trip.dropoff_address[:20]}",
                            'amount': f"₦{fare.estimated_fare:,.2f}",
                            'order_id': str(trip.id)[:8],
                            'cta_link': "https://cprohub.vercel.app/dashboard/driving"
                        }
                    )
        except Exception as e:
            logger.error(f"Failed to send email to driver: {e}")

    async def _acceptance_timeout(
        self, trip_id: uuid.UUID, driver_id: uuid.UUID, rider_id_str: str
    ):
        """
        Background task: if the driver doesn't accept within ACCEPT_TIMEOUT_SECONDS,
        auto-cancel the trip and notify the rider.
        """
        await asyncio.sleep(ACCEPT_TIMEOUT_SECONDS)

        # We need a fresh DB session — this task runs outside the request lifecycle.
        # Import here to avoid circular deps; the session factory is used directly.
        from app.db.session import get_session as _get_session
        from sqlmodel.ext.asyncio.session import AsyncSession as _AsyncSession

        async for session in _get_session():
            repo = TripRepository(session)
            trip = await repo.get_by_id(trip_id)
            if trip and trip.status == TripStatus.PENDING:
                trip.status = TripStatus.CANCELLED
                await repo.update(trip)
                await self.redis_loc.set_availability(driver_id, available=True)
                timeout_payload = {
                    "type": "ride_request_timeout",
                    "trip_id": str(trip_id),
                    "message": "Driver did not respond in time. Trip cancelled.",
                }
                await self.manager.send_to_user(rider_id_str, timeout_payload)
                await self.manager.send_to_user(str(driver_id), timeout_payload)
                logger.info("Trip %s auto-cancelled due to acceptance timeout", trip_id)
            break  # Only need one iteration

    async def _publish_to_ride_channel(self, trip_id: uuid.UUID, payload: dict):
        """Publish a message to the Redis ride:{trip_id} channel."""
        if self.manager._redis:
            try:
                import json
                await self.manager._redis.publish(
                    f"ride:{trip_id}",
                    json.dumps(payload),
                )
            except Exception:
                logger.exception("Failed to publish to ride channel %s", trip_id)
