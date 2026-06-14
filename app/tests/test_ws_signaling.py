import pytest
import uuid
import json
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import get_access_token
from app.db.session import get_session
from app.repositories.user_repo import create_user
from app.schemas.user import UserCreate

@pytest.mark.asyncio
async def test_websocket_signaling():
    # Setup database session to create a test user
    async for session in get_session():
        db = session
        break

    # Create a test user
    email = f"test_ws_{uuid.uuid4().hex[:8]}@example.com"
    username = f"test_ws_{uuid.uuid4().hex[:8]}"
    user_payload = UserCreate(email=email, username=username, password="password123", referral_code=None)
    user = await create_user(db, user_payload, password="hashed_password")

    # Generate a JWT access token for the test user
    jwt_token = await get_access_token(str(user.id))

    # Synchronous TestClient for WebSocket interactions
    client = TestClient(app)
    
    # Establish WebSocket connection
    with client.websocket_connect(f"/chat/ws?token={jwt_token}") as websocket:
        # Send a join action message
        join_payload = {
            "action": "join",
            "conversation_id": "test-conversation-id"
        }
        websocket.send_json(join_payload)
        
        # Consume the joined confirmation message
        joined_response = websocket.receive_json()
        assert joined_response["action"] == "joined"
        assert joined_response["conversation_id"] == "test-conversation-id"
        
        # Test call invite signaling
        invite_payload = {
            "action": "call_invite",
            "conversation_id": "test-conversation-id",
            "channel_name": "test-channel"
        }
        websocket.send_json(invite_payload)
        
        # Receive broadcast message
        response = websocket.receive_json()
        assert response["action"] == "call_invite"
        assert response["conversation_id"] == "test-conversation-id"
        assert response["channel_name"] == "test-channel"
        assert "caller_name" in response
        assert response["user_id"] == str(user.id)

    # Clean up the test user
    await db.delete(user)
    await db.commit()
