import asyncio
import sys
import os
import uuid
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.session import engine
from app.services.fee_service import fee_service
from app.models.admin import PlatformFeeConfig, PlatformRevenueLog, FeeType
from app.models.user import Users

async def run_tests():
    print("🧪 Running Platform Fee Logic Tests...")
    async with AsyncSession(engine, expire_on_commit=False) as db:
        # Get or create an actual user to pass the foreign key constraint
        user_stmt = select(Users).limit(1)
        user_res = await db.execute(user_stmt)
        user = user_res.scalars().first()
        created_dummy_user = False
        if not user:
            print("No users found in database, creating a dummy user...")
            user = Users(
                username="testfeeuser",
                email="testfee@example.com",
                password_hash="testpassword",
                is_active=True
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
            created_dummy_user = True

        print(f"Using user: {user.username} ({user.id})")

        # 1. Fetch config and assert default values
        config = await fee_service.get_fee_config(db)
        print(f"Platform fee config ID: {config.id}")

        # Save old config values to restore later
        old_escrow_enabled = config.escrow_release_fee_enabled
        old_escrow_type = config.escrow_release_fee_type
        old_escrow_value = config.escrow_release_fee_value

        old_deposit_enabled = config.deposit_fee_enabled
        old_deposit_type = config.deposit_fee_type
        old_deposit_value = config.deposit_fee_value

        old_withdrawal_enabled = config.withdrawal_fee_enabled
        old_withdrawal_type = config.withdrawal_fee_type
        old_withdrawal_value = config.withdrawal_fee_value

        # Update config for testing
        config.escrow_release_fee_enabled = True
        config.escrow_release_fee_type = FeeType.percentage
        config.escrow_release_fee_value = 5.0

        config.deposit_fee_enabled = True
        config.deposit_fee_type = FeeType.flat
        config.deposit_fee_value = 15000.0  # ₦150.00 flat fee

        config.withdrawal_fee_enabled = True
        config.withdrawal_fee_type = FeeType.percentage
        config.withdrawal_fee_value = 1.5   # 1.5%

        db.add(config)
        await db.commit()
        await db.refresh(config)

        # 2. Test fee calculations
        # Escrow release: 5% of ₦10,000 (1,000,000 cents) = ₦500 (50,000 cents)
        escrow_amt = 1000000
        fee_cents, net_cents = await fee_service.apply_fee(
            db=db,
            event_type="escrow_release",
            user_id=user.id,
            gross_amount_cents=escrow_amt,
            reference="TEST-ESCROW-1"
        )
        print(f"\n[Escrow Payout] Gross: {escrow_amt} cents | Fee: {fee_cents} cents | Net: {net_cents} cents")
        assert fee_cents == 50000, f"Expected 50000, got {fee_cents}"
        assert net_cents == 950000, f"Expected 950000, got {net_cents}"

        # Deposit: Flat ₦150 (15,000 cents) on any deposit of e.g. ₦5,000 (500,000 cents)
        dep_amt = 500000
        fee_cents, net_cents = await fee_service.apply_fee(
            db=db,
            event_type="deposit",
            user_id=user.id,
            gross_amount_cents=dep_amt,
            reference="TEST-DEP-1"
        )
        print(f"[Deposit] Gross: {dep_amt} cents | Fee: {fee_cents} cents | Net: {net_cents} cents")
        assert fee_cents == 15000, f"Expected 15000, got {fee_cents}"
        assert net_cents == 485000, f"Expected 485000, got {net_cents}"

        # Withdrawal: 1.5% of ₦20,000 (2,000,000 cents) = ₦300 (30,000 cents)
        wdr_amt = 2000000
        fee_cents, net_cents = await fee_service.apply_fee(
            db=db,
            event_type="withdrawal",
            user_id=user.id,
            gross_amount_cents=wdr_amt,
            reference="TEST-WDR-1"
        )
        print(f"[Withdrawal] Gross: {wdr_amt} cents | Fee: {fee_cents} cents | Net: {net_cents} cents")
        assert fee_cents == 30000, f"Expected 30000, got {fee_cents}"
        assert net_cents == 1970000, f"Expected 1970000, got {net_cents}"

        # 3. Verify revenue logs were stored
        await db.commit() # save tests logs to verify db integration

        stmt = select(PlatformRevenueLog).where(PlatformRevenueLog.reference.like("TEST-%"))
        res = await db.execute(stmt)
        logs = res.scalars().all()
        print(f"\nSaved Test Revenue Logs count: {len(logs)}")
        for log in logs:
            print(f"- {log.event_type} | Gross: {log.gross_amount_cents} | Fee: {log.fee_amount_cents} | Ref: {log.reference}")

        # Clean up test logs
        for log in logs:
            await db.delete(log)

        # Restore original config
        config.escrow_release_fee_enabled = old_escrow_enabled
        config.escrow_release_fee_type = old_escrow_type
        config.escrow_release_fee_value = old_escrow_value
        config.deposit_fee_enabled = old_deposit_enabled
        config.deposit_fee_type = old_deposit_type
        config.deposit_fee_value = old_deposit_value
        config.withdrawal_fee_enabled = old_withdrawal_enabled
        config.withdrawal_fee_type = old_withdrawal_type
        config.withdrawal_fee_value = old_withdrawal_value
        db.add(config)

        if created_dummy_user:
            await db.delete(user)

        await db.commit()
        print("\n🧹 Cleaned up test logs, dummy user and restored configs successfully.")
        print("✅ All Platform Fee Logic Tests Passed Successfully!")

if __name__ == "__main__":
    asyncio.run(run_tests())
