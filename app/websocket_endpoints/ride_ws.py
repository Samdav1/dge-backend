"""
ride_ws.py
----------
WebSocket endpoint for real-time ride events.

Channel: /ws/ride/{trip_id}?token=<jwt>

Who connects:
  - The RIDER (receives: location_update, ride_accepted, ride_completed, ride_cancelled)
  - The DRIVER (receives: ride_request, ride_cancelled, ride_request_timeout)

All events are delivered via the shared ConnectionManager which uses Redis Pub/Sub
on the channel `ride:{trip_id}`. The MatchingService publishes events there and
this endpoint relays them to locally-connected WebSocket clients.
"""

import json
import logging
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
from jose import JWTError
from jose import jwt as jose_jwt

logger = logging.getLogger(__name__)

router = APIRouter()

from app.core.security import PUBLIC_KEY

def _get_public_key() -> str:
    return PUBLIC_KEY


def _decode_token(token: str) -> Optional[str]:
    """Decode JWT access token and return the user_id string, or None on failure."""
    try:
        payload = jose_jwt.decode(token, _get_public_key(), algorithms=["RS256"])
        return payload.get("sub")
    except (JWTError, Exception) as e:
        logger.warning("ride_ws: invalid token — %s", e)
        return None


@router.websocket("/ws/ride/{trip_id}")
async def ride_websocket(
    websocket: WebSocket,
    trip_id: uuid.UUID,
    token: Optional[str] = Query(default=None),
):
    """
    WebSocket room for a single trip.

    Authentication: pass the JWT access token as ?token=<jwt> in the query string.
    Both the rider and driver connect to the same room (identified by trip_id) and
    receive all events published by the MatchingService.

    Heartbeat: client may send the text "ping" to receive "pong" back.
    """
    # Import here to avoid circular imports (manager is a module-level singleton)
    from app.dependencies.socket_connection import manager

    # ---- Authenticate ------------------------------------------------------
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    user_id = _decode_token(token)
    if not user_id:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # Use the trip_id as the "conversation" room key (ride_ prefix avoids collisions)
    room_id = f"ride_{trip_id}"

    # ---- Connect and join the ride room -----------------------------------
    await manager.connect(user_id, websocket)
    await manager.join_conversation(room_id, user_id)

    logger.info("ride_ws: user %s joined room %s", user_id, room_id)

    try:
        while True:
            # Keep connection alive; all outbound data is server-pushed.
            # Accept heartbeat pings from clients.
            data = await websocket.receive_text()
            if data.strip() == "ping":
                await websocket.send_text("pong")
            # Future: could handle client-side ack events here
    except WebSocketDisconnect:
        logger.info("ride_ws: user %s left room %s", user_id, room_id)
    finally:
        await manager.leave_conversation(room_id, user_id)
        await manager.disconnect(user_id, websocket)
