import pytest
import uuid
import os
from httpx import AsyncClient
from app.main import app
from app.core.security import get_access_token
from app.db.session import get_session
from app.repositories.user_repo import create_user
from app.schemas.user import UserCreate
from app.models.kyc import KYC, KYCStatus
from sqlalchemy import select

@pytest.mark.asyncio
async def test_kyc_gate_enforcement():
    # Setup database session
    async for session in get_session():
        db = session
        break

    # Create a unique test user
    email = f"test_kyc_{uuid.uuid4().hex[:8]}@example.com"
    username = f"test_kyc_{uuid.uuid4().hex[:8]}"
    user_payload = UserCreate(email=email, username=username, password="password123", referral_code=None)
    user = await create_user(db, user_payload, password="hashed_password")

    # Generate token
    jwt_token = await get_access_token(str(user.id))
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "X-API-KEY": os.getenv("API_KEY", ""),
    }

    # Verify that creating a service is blocked (403)
    async with AsyncClient(app=app, base_url="http://test", follow_redirects=True) as ac:
        service_data = {
            "name": "Test Service",
            "description": "Test Description",
            "price_cents": 500000, # ₦5000
            "delivery_days": 3,
        }
        res_service = await ac.post("/services/services/", data=service_data, headers=headers)
        assert res_service.status_code == 403, f"Expected 403, got {res_service.status_code}: {res_service.text}"
        assert "KYC verification required" in res_service.text

        # Verify that posting a job is blocked (403)
        job_data = {
            "title": "Need Help Request",
            "description": "Help Description",
            "min_price_cents": 100000,
            "max_price_cents": 500000,
        }
        res_job = await ac.post("/posted_jobs/", json=job_data, headers=headers)
        assert res_job.status_code == 403, f"Expected 403, got {res_job.status_code}: {res_job.text}"
        assert "KYC verification required" in res_job.text

        # Verify that creating negotiation is blocked (403)
        neg_data = {
            "service_id": str(uuid.uuid4()),
            "receiver_id": str(uuid.uuid4()),
            "proposed_price_cents": 250000,
            "message": "Negotiation Message",
        }
        res_neg = await ac.post("/price_negotiation/", json=neg_data, headers=headers)
        assert res_neg.status_code == 403, f"Expected 403, got {res_neg.status_code}: {res_neg.text}"
        assert "KYC verification required" in res_neg.text

        # ----------------------------------------------------
        # Now, create a verified KYC record for the user
        # ----------------------------------------------------
        kyc = KYC(
            user_id=user.id,
            status=KYCStatus.verified,
            metamap_verification_id="dummy_verif_id",
            document_type="national_id"
        )
        db.add(kyc)
        await db.commit()

        # Try to post a job again (should get a status code other than 403 - e.g. 400 because wallet balance is 0, but NOT 403)
        res_job_post_kyc = await ac.post("/posted_jobs/", json=job_data, headers=headers)
        assert res_job_post_kyc.status_code != 403, f"Expected non-403 status, got {res_job_post_kyc.status_code}: {res_job_post_kyc.text}"

        # Clean up
        await db.delete(kyc)
        await db.delete(user)
        await db.commit()
