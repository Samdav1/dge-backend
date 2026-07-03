import pytest
import uuid
import os
from httpx import AsyncClient
from app.main import app
from app.core.security import get_access_token
from app.db.session import engine
from app.repositories.user_repo import create_user
from app.schemas.user import UserCreate
from app.models.driving import DriverProfile, DriverStatus, DriverRank
from app.models.kyc import KYC, KYCStatus
from app.models.profile import Profile
from sqlmodel.ext.asyncio.session import AsyncSession

@pytest.mark.asyncio
async def test_admin_driver_license_flow():
    async with AsyncSession(engine, expire_on_commit=False) as db:
        # 1. Create a user
        email = f"driver_test_{uuid.uuid4().hex[:8]}@example.com"
        username = f"driver_test_{uuid.uuid4().hex[:8]}"
        user = await create_user(db, UserCreate(email=email, username=username, password="password123", referral_code=None), password="hashed")

        # 2. Add KYC profile for user
        kyc = KYC(
            user_id=user.id,
            status=KYCStatus.verified,
            first_name="John",
            last_name="Doe",
            nationality="Nigerian",
            metamap_verification_id="meta-123"
        )
        db.add(kyc)

        # 3. Create a driver profile
        driver = DriverProfile(
            user_id=user.id,
            car_name="Toyota",
            car_model="Camry",
            plate_number="ABJ-123",
            vehicle_type="car",
            license_number="LIC-12345",
            license_status="pending",
            license_picture_url="/static/license.jpg",
            car_picture_url="/static/car.jpg",
            status=DriverStatus.PENDING,
            rank=DriverRank.STARTER
        )
        db.add(driver)
        await db.commit()

        # Generate access token
        admin_headers = {
            "X-API-KEY": os.getenv("API_KEY", "vo59nkWcjkAtpPosuyqkaF3PDO1llaTT0QQA4JH0ECw3gLDDm9/awTin+wyPvgXLR7iLhTRuXvzs0KcuTe12xw=="),
        }

        async with AsyncClient(app=app, base_url="http://test") as ac:
            # 4. List pending driver licenses
            res_list = await ac.get("/super_admin/super_admins/admin-drivers/licenses?status=pending", headers=admin_headers)
            assert res_list.status_code == 200, res_list.text
            list_data = res_list.json()
            assert "items" in list_data
            assert len(list_data["items"]) > 0
            
            # Find our created driver
            found_driver = [d for d in list_data["items"] if str(d["user_id"]) == str(user.id)]
            assert len(found_driver) == 1
            assert found_driver[0]["license_number"] == "LIC-12345"
            assert found_driver[0]["license_status"] == "PENDING"

            # 5. Get detail view of the driver license
            res_detail = await ac.get(f"/super_admin/super_admins/admin-drivers/licenses/{driver.id}", headers=admin_headers)
            assert res_detail.status_code == 200, res_detail.text
            detail_data = res_detail.json()
            assert detail_data["license_number"] == "LIC-12345"
            assert detail_data["personal_info"]["car_name"] == "Toyota"
            assert detail_data["license_picture_url"] == "/static/license.jpg"

            # 6. Reject the driver license with reason
            reject_payload = {
                "action": "reject",
                "rejection_reason": "Blurred photo of license."
            }
            res_reject = await ac.post(f"/super_admin/super_admins/admin-drivers/licenses/{driver.id}/review", json=reject_payload, headers=admin_headers)
            assert res_reject.status_code == 200, res_reject.text
            reject_data = res_reject.json()
            assert reject_data["status"] == "REJECTED"

            # Verify in list of rejected
            res_list_rej = await ac.get("/super_admin/super_admins/admin-drivers/licenses?status=rejected", headers=admin_headers)
            assert res_list_rej.status_code == 200
            rej_items = res_list_rej.json()["items"]
            assert any(str(d["user_id"]) == str(user.id) for d in rej_items)

            # 7. Approve the driver license
            approve_payload = {
                "action": "approve"
            }
            res_approve = await ac.post(f"/super_admin/super_admins/admin-drivers/licenses/{driver.id}/review", json=approve_payload, headers=admin_headers)
            assert res_approve.status_code == 200, res_approve.text
            approve_data = res_approve.json()
            assert approve_data["status"] == "VERIFIED"

            # Verify in list of verified
            res_list_ver = await ac.get("/super_admin/super_admins/admin-drivers/licenses?status=verified", headers=admin_headers)
            assert res_list_ver.status_code == 200
            ver_items = res_list_ver.json()["items"]
            assert any(str(d["user_id"]) == str(user.id) for d in ver_items)

        # Cleanup DB records
        db_driver = await db.get(DriverProfile, driver.id)
        if db_driver:
            await db.delete(db_driver)
        db_kyc = await db.get(KYC, user.id)
        if db_kyc:
            await db.delete(db_kyc)
        await db.delete(user)
        await db.commit()
