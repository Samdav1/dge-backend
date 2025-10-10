# app/websocket/__init__.py

from fastapi import APIRouter
from .chat_ws import router as chat_ws_router
from .call_ws import router as call_ws_router
# from .notify_ws import router as notify_ws_router  # if you have more

# Create one combined router
router = APIRouter()

# Include all WebSocket routes
router.include_router(chat_ws_router)
router.include_router(call_ws_router)
