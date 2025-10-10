import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlmodel.ext.asyncio.session import AsyncSession

from app.dependencies.call_manager import CallManager
from app.dependencies.admin_auth import get_current_user_ws
from app.db.session import get_session

router = APIRouter()
manager = CallManager()


@router.websocket("/ws/call")
async def websocket_call(
        websocket: WebSocket,
        token: str = Query(...),
        db: AsyncSession = Depends(get_session),
):
    """Handles WebRTC signaling through authenticated WebSocket."""
    user = await get_current_user_ws(token=token, db=db)  # decode JWT and get user info
    if not user:
        await websocket.close(code=4001)
        return

    user_id = str(user.id)
    await manager.connect(user_id, websocket)

    try:
        while True:
            raw_data = await websocket.receive_text()
            msg = json.loads(raw_data)
            receiver_id = msg["receiver_id"]
            signal = msg["signal"]

            await manager.send_signal(sender=user_id, receiver=receiver_id, signal_data=signal)

    except WebSocketDisconnect:
        await manager.disconnect(user_id)
