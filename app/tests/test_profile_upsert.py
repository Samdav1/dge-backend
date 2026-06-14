import pytest
import uuid
import os
from httpx import AsyncClient
from app.main import app
from app.core.security import get_access_token
from app.db.session import get_session
from app.repositories.user_repo import create_user
from app.schemas.user import UserCreate
from app.models.profile import Profile
from sqlalchemy import select

@pytest.mark.asyncio
async def test_profile_upsert_logic():
    # Setup database session to create a test user
    async for session in get_session():
        db = session
        break

    # Create a unique test user
    email = f"test_profile_{uuid.uuid4().hex[:8]}@example.com"
    username = f"test_profile_{uuid.uuid4().hex[:8]}"
    user_payload = UserCreate(email=email, username=username, password="password123", referral_code=None)
    user = await create_user(db, user_payload, password="hashed_password")

    # Generate a JWT access token for the test user
    jwt_token = await get_access_token(str(user.id))

    # Perform PATCH /profile/update_profile to create a profile (since one doesn't exist)
    async with AsyncClient(app=app, base_url="http://test") as ac:
        headers = {
            "Authorization": f"Bearer {jwt_token}",
            "X-API-KEY": os.getenv("API_KEY", ""),
        }
        data = {
            "first_name": "TestFirst",
            "last_name": "TestLast",
            "gender": "male",
            "country": "TestCountry"
        }
        response = await ac.patch("/profile/update_profile", data=data, headers=headers)

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        res_data = response.json()
        assert res_data["first_name"] == "TestFirst"
        assert res_data["last_name"] == "TestLast"
        assert res_data["country"] == "TestCountry"

        # Perform PATCH /profile/update_profile again to update the profile
        data_update = {
            "first_name": "UpdatedFirst",
            "last_name": "UpdatedLast"
        }
        response_update = await ac.patch("/profile/update_profile", data=data_update, headers=headers)
        assert response_update.status_code == 200, f"Expected 200, got {response_update.status_code}: {response_update.text}"
        res_data_update = response_update.json()
        assert res_data_update["first_name"] == "UpdatedFirst"
        assert res_data_update["last_name"] == "UpdatedLast"
        assert res_data_update["country"] == "TestCountry"  # Should retain country value

        # Clean up database records (cascade manually)
        stmt = select(Profile).where(Profile.user_id == user.id)
        res_profile = await db.exec(stmt)
        profile = res_profile.scalars().first()
        if profile:
            await db.delete(profile)
        await db.delete(user)
        await db.commit()
