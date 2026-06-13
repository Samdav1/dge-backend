# app/api/v1/ws_chat.py
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query

from app.dependencies.admin_auth import get_current_user_ws
from app.dependencies.socket_connection import ConnectionManager
from app.db.session import get_session
from app.dependencies.auth import get_current_user
from app.repositories.messages_repo import MessageRepository
from app.schemas.user import UserRead
from app.services.messages_service import MessageService
from app.schemas.messages import MessageCreate, MessageRead
from sqlmodel.ext.asyncio.session import AsyncSession

router = APIRouter(prefix="/chat", tags=["chat"])
from app.dependencies.socket_connection import manager

from app.repositories.conversation_repo import get_user_conversations

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(None), db: AsyncSession = Depends(get_session)):
    """
    WebSocket endpoint. The client must connect with ?token=JWT or similar.
    After connection, client sends JSON with { action: 'join'|'leave'|'message'|'typing', ... }.
    """
    user = await get_current_user_ws(token=token, db=db)
    if not user:
        await websocket.close(code=1008)
        return

    user_id = str(user.id)

    # register socket for this user
    await manager.connect(user_id, websocket)

    # auto-join user to all their conversations so they receive global notifications (e.g. calls)
    user_convos = await get_user_conversations(user.id, db)
    for c in user_convos:
        await manager.join_conversation(str(c.id), user_id)

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                payload = json.loads(raw)
            except Exception:
                # ignore bad json
                continue

            action = payload.get("action")
            if action == "join":
                conv = payload.get("conversation_id")
                if conv:
                    await manager.join_conversation(conv, user_id)
                    await websocket.send_text(json.dumps({"action": "joined", "conversation_id": conv}))
                continue

            if action == "leave":
                conv = payload.get("conversation_id")
                if conv:
                    await manager.leave_conversation(conv, user_id)
                    await websocket.send_text(json.dumps({"action":"left", "conversation_id": conv}))
                continue

            if action == "typing":
                conv = payload.get("conversation_id")
                if conv:
                    await manager.broadcast_conversation(conv, {"action": "typing", "conversation_id": conv, "user_id":user_id})
                continue

            if action == "message":
                conv = payload.get("conversation_id")
                content = payload.get("content")
                ctype = payload.get("content_type", "text")
                metadata_info = payload.get("metadataInfo", {})

                if not conv or not content:
                    await websocket.send_text(json.dumps({"error": "conversation_id and content required"}))
                    continue

                # create message in DB
                repo = MessageRepository(db=db)
                service = MessageService(repo)
                msg_payload = MessageCreate(
                    conversation_id=conv,
                    sender_id=user.id,
                    content=content,
                    content_type=ctype,
                    metadataInfo=metadata_info
                )
                saved = await service.create_message(msg_payload)

                # prepare message object to send to clients
                out = {
                    "action": "message",
                    "message": {
                        "id": str(saved.id),
                        "conversation_id": str(saved.conversation_id),
                        "sender_id": str(saved.sender_id),
                        "content": saved.content,
                        "content_type": saved.content_type,
                        "created_at": saved.created_at.isoformat(),
                        "status": saved.status,
                        "metadataInfo": saved.metadataInfo
                    }
                }
                await manager.broadcast_conversation(str(conv), out)

            if action == "call_invite":
                conv = payload.get("conversation_id")
                channel_name = payload.get("channel_name")
                if conv and channel_name:
                    # Broadcast call invite to all participants in the conversation
                    invite_msg = {
                        "action": "call_invite",
                        "conversation_id": conv,
                        "channel_name": channel_name,
                        "caller_name": getattr(user, "username", None) or str(user.id),
                        "caller_avatar": "",
                        "user_id": user_id,
                    }
                    await manager.broadcast_conversation(str(conv), invite_msg)
                continue

            if action == "call_reject":
                conv = payload.get("conversation_id")
                channel_name = payload.get("channel_name", "")
                if conv:
                    reject_msg = {
                        "action": "call_reject",
                        "conversation_id": conv,
                        "channel_name": channel_name,
                        "user_id": user_id,
                    }
                    await manager.broadcast_conversation(str(conv), reject_msg)
                continue

            if action == "call_accept":
                conv = payload.get("conversation_id")
                channel_name = payload.get("channel_name", "")
                if conv:
                    accept_msg = {
                        "action": "call_accept",
                        "conversation_id": conv,
                        "channel_name": channel_name,
                        "user_id": user_id,
                    }
                    await manager.broadcast_conversation(str(conv), accept_msg)
                continue

            # unknown action: ignore
    except WebSocketDisconnect:
        await manager.disconnect(user_id, websocket)

        if not await manager.get_user_sockets(user_id):

            convs = list(manager.conversation_members.keys())
            for conv in convs:
                await manager.leave_conversation(conv, user_id)

@router.get("/ws/{conversation_id}", include_in_schema=True)
async def websocket_docs(conversation_id: str):
    """
    ## 💬 WebSocket Endpoint for Real-time Chat

    Connect here using a WebSocket client (not Swagger).

    **Endpoint:** `ws://yourdomain.com/ws/{conversation_id}`
    **Protocol:** WebSocket

    ### Example JSON Payloads:
    - Join conversation:
      ```json
      {"action": "join", "conversation_id": "abc123"}
      ```
    - Send message:
      ```json
      {"action": "message", "conversation_id": "abc123", "user_id": "xyz", "message": "Hello!"}
      ```

    ### Responses:
    - Server will broadcast JSON:
      ```json
      {
        "conversation_id": "abc123",
        "user_id": "xyz",
        "message": "Hello!"
      }
      ```

    ⚠️ Use a WebSocket client such as:
    - [WebSocket King](https://websocketking.com)
    - [Hoppscotch.io WebSocket tab](https://hoppscotch.io)
    - Browser or frontend app.
    """
    return {"detail": "This is a WebSocket endpoint. Connect via ws://, not HTTP."}
