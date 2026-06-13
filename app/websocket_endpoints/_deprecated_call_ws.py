import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlmodel.ext.asyncio.session import AsyncSession

from app.dependencies.call_manager import get_call_manager
from app.dependencies.admin_auth import get_current_user_ws
from app.db.session import get_session

router = APIRouter()
logger = logging.getLogger(__name__)


@router.websocket("/ws/call")
async def websocket_call(
        websocket: WebSocket,
        token: str = Query(...),
        db: AsyncSession = Depends(get_session),
):
    """
    Handles WebRTC signaling through authenticated WebSocket.

    Supports the following message types:
    - Signal messages: {"receiver_id": "...", "signal": {...}}
    - Ping messages: {"action": "ping"} -> responds with {"type": "pong"}

    The server also sends periodic ping messages to keep the connection alive.
    """
    user = await get_current_user_ws(token=token, db=db)
    if not user:
        await websocket.close(code=4001, reason="Authentication failed")
        return

    user_id = str(user.id)
    manager = get_call_manager()
    await manager.connect(user_id, websocket)
    logger.info("User %s connected to call WebSocket", user_id)

    try:
        while True:
            try:
                raw_data = await websocket.receive_text()
            except Exception as e:
                logger.debug("User %s WebSocket receive error: %s", user_id, e)
                break

            # Parse JSON safely
            try:
                msg = json.loads(raw_data)
            except json.JSONDecodeError as e:
                logger.warning("User %s sent invalid JSON: %s", user_id, e)
                await websocket.send_text(json.dumps({"type": "error", "message": "Invalid JSON"}))
                continue

            # Handle ping action (client-initiated keepalive)
            action = msg.get("action")
            if action == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
                continue

            # Handle pong response (from server ping)
            if msg.get("type") == "pong":
                logger.debug("Received pong from user %s", user_id)
                continue

            # Handle signal messages
            receiver_id = msg.get("receiver_id")
            signal = msg.get("signal")

            if not receiver_id:
                logger.warning("User %s sent message without receiver_id", user_id)
                await websocket.send_text(json.dumps({"type": "error", "message": "receiver_id required"}))
                continue

            if not signal:
                logger.warning("User %s sent message without signal data", user_id)
                await websocket.send_text(json.dumps({"type": "error", "message": "signal data required"}))
                continue

            # Forward the signal
            try:
                await manager.send_signal(sender=user_id, receiver=receiver_id, signal_data=signal)
                logger.debug("Signal forwarded from %s to %s", user_id, receiver_id)
            except Exception as e:
                logger.exception("Error sending signal from %s to %s: %s", user_id, receiver_id, e)
                await websocket.send_text(json.dumps({"type": "error", "message": "Failed to send signal"}))

    except WebSocketDisconnect as e:
        logger.info("User %s WebSocket disconnected: code=%s", user_id, e.code)
    except Exception as e:
        logger.exception("Unexpected error for user %s: %s", user_id, e)
    finally:
        await manager.disconnect(user_id)
        logger.info("User %s cleaned up from call WebSocket", user_id)
