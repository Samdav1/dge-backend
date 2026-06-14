import pytest
import uuid
import os
from httpx import AsyncClient
from app.main import app
from app.core.security import get_access_token
from app.db.session import get_session
from app.repositories.user_repo import create_user
from app.schemas.user import UserCreate
from app.config import settings

@pytest.mark.asyncio
async def test_get_agora_token_endpoint():
    # Setup database session to create a test user
    async for session in get_session():
        db = session
        break

    # Create a unique test user
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    username = f"test_{uuid.uuid4().hex[:8]}"
    user_payload = UserCreate(email=email, username=username, password="password123", referral_code=None)
    user = await create_user(db, user_payload, password="hashed_password")

    # Generate a JWT access token for the test user
    jwt_token = await get_access_token(str(user.id))

    # Perform the API request using AsyncClient
    async with AsyncClient(app=app, base_url="http://test") as ac:
        headers = {
            "Authorization": f"Bearer {jwt_token}",
            "X-API-KEY": os.getenv("API_KEY", ""),
        }
        payload = {
            "channel_name": "test-channel",
            "uid": 0,
            "role": 1,
            "expire_seconds": 3600
        }
        response = await ac.post("/calls/calls/agora/token", json=payload, headers=headers)

        # Assertions
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "token" in data
        assert data["channel_name"] == "test-channel"
        assert data["app_id"] == settings.agora_app_id
        assert data["uid"] == 0

        # Clean up the test user
        await db.delete(user)
        await db.commit()
