import uuid
from datetime import datetime, timezone
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from app.models.admin import PlatformFeeConfig, PlatformRevenueLog, FeeType


class FeeService:
    async def get_fee_config(self, db: AsyncSession) -> PlatformFeeConfig:
        """Fetch the single platform fee config row, creating it with defaults if missing."""
        stmt = select(PlatformFeeConfig).where(PlatformFeeConfig.id == 1)
        res = await db.execute(stmt)
        config = res.scalars().first()
        if not config:
            config = PlatformFeeConfig(id=1)
            db.add(config)
            await db.commit()
            await db.refresh(config)
        return config

    def calculate_fee(self, amount_cents: int, fee_type: FeeType, fee_value: float) -> int:
        """Calculate the fee in cents based on the type (percentage or flat)."""
        if fee_type == FeeType.percentage:
            fee = int(amount_cents * (fee_value / 100.0))
        else:
            # Flat fee value is in cents (e.g. 500 = ₦5.00)
            fee = int(fee_value)
        return max(0, min(fee, amount_cents))

    async def apply_fee(
        self,
        db: AsyncSession,
        event_type: str,
        user_id: uuid.UUID,
        gross_amount_cents: int,
        reference: str
    ) -> tuple[int, int]:
        """
        Calculates and records the platform fee for a given payment event.
        Returns a tuple of (fee_cents, net_amount_cents).
        """
        config = await self.get_fee_config(db)

        enabled = False
        fee_type = FeeType.percentage
        fee_value = 0.0

        if event_type == "escrow_release":
            enabled = config.escrow_release_fee_enabled
            fee_type = config.escrow_release_fee_type
            fee_value = config.escrow_release_fee_value
        elif event_type == "deposit":
            enabled = config.deposit_fee_enabled
            fee_type = config.deposit_fee_type
            fee_value = config.deposit_fee_value
        elif event_type == "withdrawal":
            enabled = config.withdrawal_fee_enabled
            fee_type = config.withdrawal_fee_type
            fee_value = config.withdrawal_fee_value

        if not enabled or gross_amount_cents <= 0:
            return 0, gross_amount_cents

        fee_cents = self.calculate_fee(gross_amount_cents, fee_type, fee_value)
        net_cents = gross_amount_cents - fee_cents

        if fee_cents > 0:
            log = PlatformRevenueLog(
                event_type=event_type,
                user_id=user_id,
                gross_amount_cents=gross_amount_cents,
                fee_amount_cents=fee_cents,
                fee_type=fee_type,
                fee_value=fee_value,
                reference=reference
            )
            db.add(log)
            # Do not commit yet, let the calling service control transaction boundaries.

        return fee_cents, net_cents


fee_service = FeeService()
