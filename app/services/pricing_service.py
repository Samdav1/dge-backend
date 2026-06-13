"""
pricing_service.py
------------------
Pure-function pricing engine — no database access, no side effects.
All calculations are deterministic and easily unit-testable.

Fare formula:
    fare = max(MIN_FARE, (BASE_FARE + RATE_PER_KM * distance_km) * surge_multiplier)

Default rates (override via env or pass explicitly):
    BASE_FARE   = 1.50 USD
    RATE_PER_KM = 0.35 USD/km
    MIN_FARE    = 2.50 USD
"""

import math
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Rate constants  (can be overridden at call site or via dependency injection)
# ---------------------------------------------------------------------------
BASE_FARE: float = 500.0      # NGN — flat flag-fall
RATE_PER_KM: float = 300.0    # NGN per kilometre
MIN_FARE: float = 1000.0      # NGN — minimum charge per trip


# ---------------------------------------------------------------------------
# Haversine distance
# ---------------------------------------------------------------------------

def haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Returns the great-circle distance in kilometres between two GPS coordinates
    using the Haversine formula.

    Args:
        lat1, lng1: Pickup latitude / longitude (decimal degrees)
        lat2, lng2: Dropoff latitude / longitude (decimal degrees)

    Returns:
        Distance in kilometres (float, >= 0)
    """
    R = 6371.0  # Earth's mean radius in km

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)

    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return round(R * c, 4)


# ---------------------------------------------------------------------------
# Fare estimation
# ---------------------------------------------------------------------------

@dataclass
class FareBreakdown:
    """Detailed fare receipt returned to both rider and driver."""
    distance_km: float
    base_fare: float
    distance_charge: float
    surge_multiplier: float
    estimated_fare: float   # Total rounded to 2 d.p.


def estimate_fare(
    distance_km: float,
    surge_multiplier: float = 1.0,
    base_fare: float = BASE_FARE,
    rate_per_km: float = RATE_PER_KM,
    min_fare: float = MIN_FARE,
) -> FareBreakdown:
    """
    Calculate the estimated fare for a trip.

    Args:
        distance_km:      Straight-line or route distance in km.
        surge_multiplier: Demand-based multiplier (1.0 = normal, 2.0 = surge).
        base_fare:        Flat flag-fall charge in USD.
        rate_per_km:      Per-km rate in USD.
        min_fare:         Minimum fare regardless of distance.

    Returns:
        FareBreakdown dataclass with itemised charges.
    """
    distance_charge = rate_per_km * distance_km
    subtotal = (base_fare + distance_charge) * surge_multiplier
    total = round(max(min_fare, subtotal), 2)

    return FareBreakdown(
        distance_km=round(distance_km, 3),
        base_fare=base_fare,
        distance_charge=round(distance_charge, 2),
        surge_multiplier=surge_multiplier,
        estimated_fare=total,
    )


def calculate_trip_fare(
    pickup_lat: float,
    pickup_lng: float,
    dropoff_lat: float,
    dropoff_lng: float,
    surge_multiplier: float = 1.0,
) -> FareBreakdown:
    """
    Convenience wrapper: compute distance then price in one call.
    Used by the Matching Engine when creating a new Trip record.
    """
    dist = haversine(pickup_lat, pickup_lng, dropoff_lat, dropoff_lng)
    return estimate_fare(dist, surge_multiplier)
