"""
redis_location.py
-----------------
High-performance driver location cache backed by Redis GEO commands.

Key space:
  geo:drivers                   → GEO sorted set; member = str(driver_id)
  driver:avail:{driver_id}      → "1" (available) | "0" (on trip)
  driver:loc:{driver_id}        → HASH { lat, lng, updated_at }

Why Redis GEO instead of PostgreSQL Haversine?
  - GEOSEARCH is O(N+log M) where N = results; no full table scan.
  - Lat/lng writes are in-memory only (microseconds vs milliseconds for SQL).
  - PostGIS would be the SQL equivalent for production scale-out.
"""

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

GEO_KEY = "geo:drivers"
AVAIL_PREFIX = "driver:avail:"
LOC_PREFIX = "driver:loc:"
DEFAULT_RADIUS_KM = 5.0
DEFAULT_LIMIT = 20


class RedisLocationService:
    """Manages real-time driver GPS data using Redis GEO commands."""

    def __init__(self, redis_client: aioredis.Redis):
        self._r = redis_client

    # ------------------------------------------------------------------
    # Write path  (called on every GPS ping from driver app)
    # ------------------------------------------------------------------

    async def update_location(
        self,
        driver_id: UUID,
        lat: float,
        lng: float,
        available: bool = True,
    ) -> None:
        """
        Upsert driver position in the Redis GEO index and availability flag.
        Redis GEOADD uses (longitude, latitude) order — note the swap.
        """
        sid = str(driver_id)
        pipe = self._r.pipeline(transaction=False)
        # GEO set — longitude FIRST per Redis spec
        pipe.geoadd(GEO_KEY, [lng, lat, sid])
        # Availability bit
        pipe.set(f"{AVAIL_PREFIX}{sid}", "1" if available else "0")
        # Human-readable location hash (useful for debugging / admin panels)
        pipe.hset(
            f"{LOC_PREFIX}{sid}",
            mapping={
                "lat": lat,
                "lng": lng,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        try:
            await pipe.execute()
        except Exception:
            logger.exception("RedisLocationService.update_location failed for driver %s", sid)

    async def set_availability(self, driver_id: UUID, available: bool) -> None:
        """Flip the availability flag without touching position data."""
        try:
            await self._r.set(f"{AVAIL_PREFIX}{str(driver_id)}", "1" if available else "0")
        except Exception:
            logger.exception("RedisLocationService.set_availability failed for driver %s", driver_id)

    async def remove_driver(self, driver_id: UUID) -> None:
        """Remove driver from GEO index (e.g. when they go offline)."""
        sid = str(driver_id)
        pipe = self._r.pipeline(transaction=False)
        pipe.zrem(GEO_KEY, sid)
        pipe.delete(f"{AVAIL_PREFIX}{sid}")
        pipe.delete(f"{LOC_PREFIX}{sid}")
        await pipe.execute()

    # ------------------------------------------------------------------
    # Read path  (called when rider requests a ride)
    # ------------------------------------------------------------------

    async def find_nearby_available(
        self,
        lat: float,
        lng: float,
        radius_km: float = DEFAULT_RADIUS_KM,
        limit: int = DEFAULT_LIMIT,
    ) -> list[dict]:
        """
        Return up to `limit` available drivers within `radius_km` of (lat, lng),
        sorted by distance (nearest first).

        Returns list of dicts: { driver_id: str, distance_km: float }
        """
        try:
            # GEOSEARCH FROMLONLAT <lng> <lat> BYRADIUS <radius> km ASC COUNT <limit> WITHCOORD WITHDIST
            # redis-py >= 4.1 exposes geosearch()
            raw = await self._r.geosearch(
                GEO_KEY,
                longitude=lng,
                latitude=lat,
                radius=radius_km,
                unit="km",
                sort="ASC",
                count=limit,
                withdist=True,
                withcoord=True,
            )
        except Exception:
            logger.exception("RedisLocationService.find_nearby_available: geosearch failed")
            return []

        if not raw:
            return []

        results = []
        for item in raw:
            # redis-py returns (member, dist, (lng, lat)) when withdist=True, withcoord=True
            member, dist, coord = item[0], item[1], item[2]
            lng, lat = coord
            sid = member.decode() if isinstance(member, bytes) else str(member)

            # Check availability flag
            avail_raw = await self._r.get(f"{AVAIL_PREFIX}{sid}")
            if avail_raw is None:
                # No flag stored — treat as unavailable (safer default)
                continue
            avail_val = avail_raw.decode() if isinstance(avail_raw, bytes) else str(avail_raw)
            if avail_val != "1":
                continue

            results.append({
                "driver_id": sid, 
                "distance_km": round(float(dist), 3),
                "lat": float(lat),
                "lng": float(lng)
            })

        return results

    async def get_location(self, driver_id: UUID) -> Optional[dict]:
        """
        Fetch the cached position hash for a single driver.
        Returns { lat, lng, updated_at } or None.
        """
        raw = await self._r.hgetall(f"{LOC_PREFIX}{str(driver_id)}")
        if not raw:
            return None
        return {
            "lat": float(raw.get(b"lat", raw.get("lat", 0))),
            "lng": float(raw.get(b"lng", raw.get("lng", 0))),
            "updated_at": (raw.get(b"updated_at", raw.get("updated_at", b""))).decode()
            if isinstance(raw.get(b"updated_at", raw.get("updated_at", "")), bytes)
            else raw.get("updated_at", ""),
        }
