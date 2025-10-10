import asyncio
import json
import os
from typing import Dict, Optional

import redis.asyncio as redis
from fastapi import WebSocket


class CallManager:
    """
    Handles WebRTC signaling via Redis Pub/Sub for multi-server scalability.
    """

    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self._redis: Optional[redis.Redis] = None
        self.user_sockets: Dict[str, WebSocket] = {}

    async def start(self):
        """Initialize Redis and start listening for pub/sub messages."""
        self._redis = redis.from_url(self.redis_url)
        asyncio.create_task(self._listen())

    async def stop(self):
        if self._redis:
            await self._redis.close()

    async def _listen(self):
        """Listen for Redis-published call messages and route locally."""
        pubsub = self._redis.pubsub(ignore_subscribe_messages=True)
        await pubsub.psubscribe("call:*")

        async for message in pubsub.listen():
            data_raw = message.get("data")
            if not data_raw:
                continue

            try:
                payload = json.loads(data_raw.decode() if isinstance(data_raw, bytes) else data_raw)
                await self._forward_local(payload)
            except Exception as e:
                print("Redis listener error:", e)

    async def _forward_local(self, payload: dict):
        """Send signaling message to local WebSocket if user is connected."""
        target_user = payload.get("target_user")
        if not target_user:
            return

        ws = self.user_sockets.get(target_user)
        if ws:
            await ws.send_text(json.dumps(payload))

    async def connect(self, user_id: str, ws: WebSocket):
        """Register a user’s WebSocket connection."""
        await self.start()
        await ws.accept()
        self.user_sockets[user_id] = ws
        print(f"User {user_id} connected for calls")

    async def disconnect(self, user_id: str):
        """Remove disconnected user's WebSocket."""
        if user_id in self.user_sockets:
            del self.user_sockets[user_id]
            print(f"User {user_id} disconnected")

    async def send_signal(self, sender: str, receiver: str, signal_data: dict):
        """
        Publish signaling data to Redis so other servers (or same one) can deliver it.
        """
        message = {
            "type": "signal",
            "sender": sender,
            "target_user": receiver,
            "data": signal_data,
        }
        await self._redis.publish(f"call:{receiver}", json.dumps(message))
