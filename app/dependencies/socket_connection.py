# app/core/connection_manager.py
from typing import Dict, Set, Optional, Callable, Any
from fastapi import WebSocket
import json
import asyncio
import os
import redis.asyncio as redis
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    ConnectionManager with Redis Pub/Sub integration.

    - Local structures (per-process):
        user_sockets: user_id -> set(WebSocket)
        conversation_members: conversation_id -> set(user_id)

    - Redis:
        * Pub/Sub channel: `conversation:{conversation_id}` - carry messages for that convo
        * Optional: Redis set `conversation:{conversation_id}:members` mirrors membership globally (helpful)
    """

    def __init__(self, redis_url: Optional[str] = None):
        # local in-memory state per process
        self.user_sockets: Dict[str, Set[WebSocket]] = {}
        self.conversation_members: Dict[str, Set[str]] = {}
        self._lock = asyncio.Lock()

        # Redis
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self._redis: Optional[redis.Redis] = None
        self._pubsub_task: Optional[asyncio.Task] = None
        self._stopped = False

    # ---------- Redis lifecycle ----------
    async def start(self):
        """Connect to redis and start pubsub listener. Call at app startup."""
        if self._redis:
            return
        self._redis = redis.from_url(self.redis_url)
        # Start background listener that handles messages published by any instance
        loop = asyncio.get_event_loop()
        self._pubsub_task = loop.create_task(self._redis_listener())
        logger.info("ConnectionManager: started Redis listener")

    async def stop(self):
        """Stop listener and close redis connection. Call at app shutdown."""
        self._stopped = True
        if self._pubsub_task:
            self._pubsub_task.cancel()
            try:
                await self._pubsub_task
            except asyncio.CancelledError:
                pass
        if self._redis:
            await self._redis.close()
            self._redis = None
        logger.info("ConnectionManager: stopped Redis listener")

    async def _redis_listener(self):
        """Subscribe to conversation:* and ride:* patterns and forward messages to local sockets."""
        assert self._redis is not None, "Redis client not started"
        pubsub = self._redis.pubsub(ignore_subscribe_messages=True)
        # Subscribe to both chat conversations and real-time ride rooms
        await pubsub.psubscribe("conversation:*", "ride:*")
        logger.info("Subscribed to Redis patterns: conversation:*, ride:*")
        try:
            async for message in pubsub.listen():
                if message is None:
                    continue
                # message example: {"type":"pmessage", "pattern":"conversation:*",
                # "channel":"conversation:conv_123", "data": b'...'}
                try:
                    # message["data"] is bytes
                    data_raw = message.get("data")
                    if data_raw is None:
                        continue
                    if isinstance(data_raw, (bytes, bytearray)):
                        payload = json.loads(data_raw.decode())
                    elif isinstance(data_raw, str):
                        payload = json.loads(data_raw)
                    else:
                        payload = data_raw

                    # Determine the room id from the channel name or payload
                    channel_raw = message.get("channel", b"")
                    channel_str = channel_raw.decode() if isinstance(channel_raw, bytes) else str(channel_raw)

                    if channel_str.startswith("ride:"):
                        # ride:{trip_id}  →  local room key is ride_{trip_id}
                        trip_id_part = channel_str.split(":", 1)[1]
                        room_id = f"ride_{trip_id_part}"
                    else:
                        # conversation:{conversation_id}
                        room_id = payload.get("conversation_id") or self._channel_to_conversation(channel_raw)

                    if not room_id:
                        logger.warning("Redis message has no room id: %s", payload)
                        continue

                    # Broadcast to local sockets in that room
                    await self._broadcast_local(room_id, payload)
                except Exception as exc:
                    logger.exception("Error handling pubsub message: %s", exc)
        except asyncio.CancelledError:
            logger.info("Redis listener cancelled")
        finally:
            try:
                await pubsub.unsubscribe()
                await pubsub.close()
            except Exception:
                pass

    @staticmethod
    def _channel_to_conversation(channel: Any) -> Optional[str]:
        """Extract conversation id from channel name 'conversation:{conversation_id}'."""
        if not channel:
            return None
        if isinstance(channel, (bytes, bytearray)):
            channel = channel.decode()
        if isinstance(channel, str) and channel.startswith("conversation:"):
            return channel.split(":", 1)[1]
        return None

    # ---------- Connection management (local) ----------
    async def connect(self, user_id: str, websocket: WebSocket):
        """Accept socket and register locally. Do NOT add to conversation sets here."""
        await websocket.accept()
        async with self._lock:
            self.user_sockets.setdefault(user_id, set()).add(websocket)
        logger.debug("User %s connected (sockets=%d)", user_id, len(self.user_sockets.get(user_id, set())))

    async def disconnect(self, user_id: str, websocket: WebSocket):
        async with self._lock:
            sockets = self.user_sockets.get(user_id)
            if sockets and websocket in sockets:
                sockets.remove(websocket)
            if not sockets:
                self.user_sockets.pop(user_id, None)
        logger.debug("User %s disconnected", user_id)

    # ---------- Conversation membership (local + optional redis mirror) ----------
    async def join_conversation(self, conversation_id: str, user_id: str, mirror_to_redis: bool = True):
        """
        Mark user as joined to conversation locally; optionally add to Redis set for global membership.
        """
        async with self._lock:
            self.conversation_members.setdefault(conversation_id, set()).add(user_id)
        if mirror_to_redis and self._redis:
            try:
                await self._redis.sadd(f"conversation:{conversation_id}:members", user_id)
            except Exception:
                logger.exception("Failed to SADD conversation members in Redis")

    async def leave_conversation(self, conversation_id: str, user_id: str, mirror_to_redis: bool = True):
        async with self._lock:
            members = self.conversation_members.get(conversation_id)
            if members:
                members.discard(user_id)
                if not members:
                    self.conversation_members.pop(conversation_id, None)
        if mirror_to_redis and self._redis:
            try:
                await self._redis.srem(f"conversation:{conversation_id}:members", user_id)
            except Exception:
                logger.exception("Failed to SREM conversation members in Redis")

    async def get_user_sockets(self, user_id: str) -> Set[WebSocket]:
        return self.user_sockets.get(user_id, set())

    async def get_conversation_members(self, conversation_id: str) -> Set[str]:
        # prefer local membership (fast), fallback to redis membership (global)
        local = self.conversation_members.get(conversation_id)
        if local:
            return local
        if self._redis:
            try:
                members = await self._redis.smembers(f"conversation:{conversation_id}:members")
                # smembers returns set of bytes; decode to str
                return set(m.decode() if isinstance(m, (bytes, bytearray)) else str(m) for m in members)
            except Exception:
                logger.exception("Failed to get members from Redis")
        return set()

    # ---------- Sending operations ----------
    async def send_to_user(self, user_id: str, message_obj: dict):
        sockets = await self.get_user_sockets(user_id)
        if not sockets:
            logger.warning("send_to_user: No active sockets for user_id=%s (connected users: %s), message type=%s",
                         user_id, list(self.user_sockets.keys()), message_obj.get('type', 'unknown'))
            return
        logger.info("send_to_user: Sending '%s' to user_id=%s (%d sockets)",
                   message_obj.get('type', 'unknown'), user_id, len(sockets))
        text = json.dumps(message_obj)
        coros = [ws.send_text(text) for ws in list(sockets)]
        await asyncio.gather(*coros, return_exceptions=True)

    async def _broadcast_local(self, conversation_id: str, message_obj: dict):
        """Broadcast message to local sockets of members who have joined locally."""
        members = self.conversation_members.get(conversation_id, set())
        # if local membership is empty, we still try to fetch from redis to know local candidates
        if not members and self._redis:
            try:
                all_members = await self._redis.smembers(f"conversation:{conversation_id}:members")
                members = set(m.decode() if isinstance(m, (bytes, bytearray)) else str(m) for m in all_members)
            except Exception:
                members = set()

        coros = []
        text = json.dumps(message_obj)
        for user_id in members:
            sockets = self.user_sockets.get(user_id, set())
            for ws in sockets:
                coros.append(ws.send_text(text))
        if coros:
            await asyncio.gather(*coros, return_exceptions=True)

    async def broadcast_conversation(self, conversation_id: str, message_obj: dict, publish_to_redis: bool = True):
        """
        Public API to broadcast a message for a conversation:
         - If publish_to_redis=True: publish the message to Redis. All instances will pick it up and local-broadcast.
         - If publish_to_redis=False: only broadcast locally (useful for tests)
        """
        # include conversation id in message payload
        payload = dict(message_obj)
        payload["conversation_id"] = conversation_id

        # First broadcast locally (so sender on same instance gets immediate delivery)
        await self._broadcast_local(conversation_id, payload)

        # Then publish to Redis so other instances receive it
        if publish_to_redis and self._redis:
            try:
                await self._redis.publish(f"conversation:{conversation_id}", json.dumps(payload))
            except Exception:
                logger.exception("Failed to publish message to Redis")

    # ---------- Utility helpers ----------
    async def list_local_users(self) -> Set[str]:
        return set(self.user_sockets.keys())

manager = ConnectionManager()
