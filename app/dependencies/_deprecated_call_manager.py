import asyncio
import json
import os
import logging
from typing import Dict, Optional

import redis.asyncio as redis
from fastapi import WebSocket
from starlette.websockets import WebSocketState

logger = logging.getLogger(__name__)

# Heartbeat interval in seconds - send ping every 25s to keep connection alive
PING_INTERVAL = 25

# Singleton instance
_call_manager_instance: Optional["CallManager"] = None


def get_call_manager() -> "CallManager":
    """Get the singleton CallManager instance."""
    global _call_manager_instance
    if _call_manager_instance is None:
        _call_manager_instance = CallManager()
    return _call_manager_instance


class CallManager:
    """
    Handles WebRTC signaling via Redis Pub/Sub for multi-server scalability.

    Features:
    - Heartbeat ping/pong to prevent connection timeouts (1006 errors)
    - Redis Pub/Sub for cross-server message delivery
    - Robust error handling and logging

    Usage:
        # Get the singleton instance
        manager = get_call_manager()

        # Start at app startup
        await manager.start()
    """

    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self._redis: Optional[redis.Redis] = None
        self.user_sockets: Dict[str, WebSocket] = {}
        self._heartbeat_tasks: Dict[str, asyncio.Task] = {}
        self._started = False
        self._stopped = False
        self._listener_task: Optional[asyncio.Task] = None

    async def start(self):
        """Initialize Redis and start listening for pub/sub messages. Call once at app startup."""
        if self._started:
            logger.debug("CallManager already started, skipping...")
            return

        self._started = True
        self._stopped = False
        self._redis = redis.from_url(self.redis_url)
        self._listener_task = asyncio.create_task(self._listen())
        logger.info("CallManager started and Redis connected")

    async def stop(self):
        """Shutdown Redis and cancel all tasks. Call at app shutdown."""
        self._stopped = True

        # Cancel all heartbeat tasks
        for user_id, task in list(self._heartbeat_tasks.items()):
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._heartbeat_tasks.clear()

        # Cancel listener task
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass

        # Close Redis
        if self._redis:
            await self._redis.close()
            self._redis = None

        self._started = False
        logger.info("CallManager stopped and Redis closed")

    async def _listen(self):
        """Listen for Redis-published call messages and route locally."""
        if not self._redis:
            logger.error("Redis client not initialized, cannot start listener")
            return

        pubsub = self._redis.pubsub(ignore_subscribe_messages=True)
        await pubsub.psubscribe("call:*")
        logger.info("CallManager: subscribed to Redis pattern call:*")

        try:
            async for message in pubsub.listen():
                if self._stopped:
                    break

                data_raw = message.get("data")
                if not data_raw:
                    continue

                try:
                    payload = json.loads(data_raw.decode() if isinstance(data_raw, bytes) else data_raw)
                    await self._forward_local(payload)
                except json.JSONDecodeError as e:
                    logger.warning("Invalid JSON in Redis message: %s", e)
                except Exception as e:
                    logger.exception("Redis listener error: %s", e)
        except asyncio.CancelledError:
            logger.info("CallManager Redis listener cancelled")
        finally:
            try:
                await pubsub.unsubscribe()
                await pubsub.close()
            except Exception:
                pass

    async def _forward_local(self, payload: dict):
        """Send signaling message to local WebSocket if user is connected."""
        target_user = payload.get("target_user")
        if not target_user:
            return

        ws = self.user_sockets.get(target_user)
        if ws and ws.client_state == WebSocketState.CONNECTED:
            try:
                await ws.send_text(json.dumps(payload))
                logger.debug("Forwarded signal to user %s", target_user)
            except Exception as e:
                logger.warning("Failed to forward signal to user %s: %s", target_user, e)

    async def _heartbeat(self, user_id: str, ws: WebSocket):
        """Send periodic ping messages to keep WebSocket connection alive."""
        try:
            while not self._stopped:
                await asyncio.sleep(PING_INTERVAL)

                if ws.client_state != WebSocketState.CONNECTED:
                    logger.debug("User %s WebSocket no longer connected, stopping heartbeat", user_id)
                    break

                try:
                    # Send a ping message the client can respond to (optional)
                    await ws.send_text(json.dumps({"type": "ping", "timestamp": asyncio.get_event_loop().time()}))
                    logger.debug("Sent ping to user %s", user_id)
                except Exception as e:
                    logger.warning("Failed to send ping to user %s: %s", user_id, e)
                    break
        except asyncio.CancelledError:
            logger.debug("Heartbeat for user %s cancelled", user_id)

    async def connect(self, user_id: str, ws: WebSocket):
        """Register a user's WebSocket connection and start heartbeat."""
        await ws.accept()

        # If user already has a connection, disconnect the old one first
        if user_id in self.user_sockets:
            old_ws = self.user_sockets[user_id]
            if old_ws.client_state == WebSocketState.CONNECTED:
                try:
                    await old_ws.close(code=1000, reason="New connection established")
                except Exception:
                    pass
            # Cancel old heartbeat
            if user_id in self._heartbeat_tasks:
                self._heartbeat_tasks[user_id].cancel()

        self.user_sockets[user_id] = ws

        # Start heartbeat for this connection
        self._heartbeat_tasks[user_id] = asyncio.create_task(self._heartbeat(user_id, ws))

        logger.info("User %s connected for calls", user_id)

    async def disconnect(self, user_id: str):
        """Remove disconnected user's WebSocket and cancel heartbeat."""
        # Cancel heartbeat task
        if user_id in self._heartbeat_tasks:
            self._heartbeat_tasks[user_id].cancel()
            try:
                await self._heartbeat_tasks[user_id]
            except asyncio.CancelledError:
                pass
            del self._heartbeat_tasks[user_id]

        # Remove socket
        if user_id in self.user_sockets:
            del self.user_sockets[user_id]

        logger.info("User %s disconnected from calls", user_id)

    async def send_signal(self, sender: str, receiver: str, signal_data: dict):
        """
        Publish signaling data to Redis so other servers (or same one) can deliver it.
        """
        if not self._redis:
            logger.error("Cannot send signal: Redis not connected")
            return

        message = {
            "type": "signal",
            "sender": sender,
            "target_user": receiver,
            "data": signal_data,
        }
        try:
            await self._redis.publish(f"call:{receiver}", json.dumps(message))
            logger.debug("Published signal from %s to %s", sender, receiver)
        except Exception as e:
            logger.exception("Failed to publish signal: %s", e)
