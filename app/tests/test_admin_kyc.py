import pytest
import uuid
import os
from httpx import AsyncClient
from app.main import app
from app.db.session import engine
from app.repositories.user_repo import create_user
from app.schemas.user import UserCreate
from app.models.kyc import KYC, KYCStatus
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

@pytest.mark.asyncio
async def test_admin_manual_kyc_approval_flow():
    async with AsyncSession(engine, expire_on_commit=False) as db:
        # 1. Create a user without any KYC submission
        email = f"kyc_test_{uuid.uuid4().hex[:8]}@example.com"
        username = f"kyc_test_{uuid.uuid4().hex[:8]}"
        user = await create_user(
            db, 
            UserCreate(email=email, username=username, password="password123", referral_code=None), 
            password="hashed"
        )
        await db.commit()

        # Admin headers
        admin_headers = {
            "X-API-KEY": os.getenv("API_KEY", "vo59nkWcjkAtpPosuyqkaF3PDO1llaTT0QQA4JH0ECw3gLDDm9/awTin+wyPvgXLR7iLhTRuXvzs0KcuTe12xw=="),
        }

        async with AsyncClient(app=app, base_url="http://test") as ac:
            # 2. Try to manually approve the user's KYC even though they didn't submit anything
            approve_payload = {
                "action": "approve"
            }
            res_approve = await ac.post(
                f"/super_admin/super_admins/admin-kyc/{user.id}/review", 
                json=approve_payload, 
                headers=admin_headers
            )
            assert res_approve.status_code == 200, res_approve.text
            approve_data = res_approve.json()
            assert approve_data["status"] == "VERIFIED"

            # 3. Verify that the KYC record was created and set to verified in the database
            res_kyc = await db.execute(select(KYC).where(KYC.user_id == user.id))
            db_kyc = res_kyc.scalar_one_or_none()
            assert db_kyc is not None
            assert db_kyc.status == KYCStatus.verified

        # Cleanup DB records
        await db.delete(db_kyc)
        await db.delete(user)
        await db.commit()
