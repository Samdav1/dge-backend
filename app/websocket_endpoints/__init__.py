# app/websocket/__init__.py

from fastapi import APIRouter
from .chat_ws import router as chat_ws_router

# Create one combined router
router = APIRouter()

# Include all WebSocket routes
router.include_router(chat_ws_router)
