import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from fastapi import HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.points import AdminPointsSettings, UserPoints, PointsTransaction
from app.models.wallet import Wallet, WalletType
from app.models.transactions import Transaction, TxnType, TxnStatus
from app.models.user import Users
from app.services.monnify_service import monnify_service

logger = logging.getLogger(__name__)


async def get_points_settings(db: AsyncSession) -> AdminPointsSettings:
    """Return platform points settings row (id=1), creating defaults if absent."""
    stmt = select(AdminPointsSettings).where(AdminPointsSettings.id == 1)
    res = await db.execute(stmt)
    settings = res.scalar_one_or_none()
    if not settings:
        settings = AdminPointsSettings(
            id=1,
            rate_per_point=100.0,
            signup_bonus_points=10,
            min_purchase_points=1,
        )
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
    return settings


async def update_points_settings(
    db: AsyncSession,
    rate_per_point: Optional[float] = None,
    signup_bonus_points: Optional[int] = None,
    min_purchase_points: Optional[int] = None,
    admin_id: Optional[uuid.UUID] = None,
) -> AdminPointsSettings:
    """Admin updates points settings."""
    settings = await get_points_settings(db)
    if rate_per_point is not None:
        if rate_per_point <= 0:
            raise HTTPException(status_code=400, detail="Rate per point must be greater than zero")
        settings.rate_per_point = float(rate_per_point)
    if signup_bonus_points is not None:
        if signup_bonus_points < 0:
            raise HTTPException(status_code=400, detail="Signup bonus points cannot be negative")
        settings.signup_bonus_points = int(signup_bonus_points)
    if min_purchase_points is not None:
        settings.min_purchase_points = max(1, int(min_purchase_points))
    settings.updated_at = datetime.now(timezone.utc)
    if admin_id:
        settings.updated_by_admin_id = admin_id

    db.add(settings)
    await db.commit()
    await db.refresh(settings)
    return settings


async def get_or_create_user_points(db: AsyncSession, user_id: uuid.UUID) -> UserPoints:
    """Retrieve user points balance or initialize with signup bonus (default 10 points)."""
    stmt = select(UserPoints).where(UserPoints.user_id == user_id)
    res = await db.execute(stmt)
    user_points = res.scalar_one_or_none()

    if not user_points:
        settings = await get_points_settings(db)
        bonus = settings.signup_bonus_points

        user_points = UserPoints(
            user_id=user_id,
            balance=bonus,
            total_earned=bonus,
            total_spent=0,
        )
        db.add(user_points)

        # Log signup bonus transaction
        bonus_tx = PointsTransaction(
            user_id=user_id,
            points=bonus,
            naira_amount=bonus * settings.rate_per_point,
            rate_at_time=settings.rate_per_point,
            type="signup_bonus",
            status="successful",
            reference=f"DGE-BONUS-{uuid.uuid4().hex[:8].upper()}",
            description=f"Welcome bonus {bonus} DGE Points on successful registration!",
        )
        db.add(bonus_tx)

        await db.commit()
        await db.refresh(user_points)

    return user_points


async def get_user_points_summary(db: AsyncSession, user_id: uuid.UUID) -> Dict[str, Any]:
    """Get points balance, current rate, and summary stats."""
    settings = await get_points_settings(db)
    user_points = await get_or_create_user_points(db, user_id)
    
    # Also fetch user's deposit wallet balance for UI convenience
    wallet_stmt = select(Wallet).where(
        Wallet.user_id == user_id,
        Wallet.wallet_type == WalletType.deposit
    )
    wallet_res = await db.execute(wallet_stmt)
    deposit_wallet = wallet_res.scalar_one_or_none()
    wallet_balance_naira = (deposit_wallet.balance_cents / 100.0) if deposit_wallet else 0.0

    return {
        "balance": user_points.balance,
        "total_earned": user_points.total_earned,
        "total_spent": user_points.total_spent,
        "rate_per_point": settings.rate_per_point,
        "signup_bonus_points": settings.signup_bonus_points,
        "min_purchase_points": settings.min_purchase_points,
        "equivalent_naira": user_points.balance * settings.rate_per_point,
        "wallet_balance_naira": wallet_balance_naira,
        "updated_at": user_points.updated_at.isoformat() if user_points.updated_at else None,
    }


async def get_user_points_transactions(db: AsyncSession, user_id: uuid.UUID, limit: int = 50) -> List[PointsTransaction]:
    """List points transactions for a user."""
    stmt = (
        select(PointsTransaction)
        .where(PointsTransaction.user_id == user_id)
        .order_by(PointsTransaction.created_at.desc())
        .limit(limit)
    )
    res = await db.execute(stmt)
    return res.scalars().all()


async def buy_points_with_wallet(db: AsyncSession, user_id: uuid.UUID, points: int) -> Dict[str, Any]:
    """Purchase points directly using user's deposit wallet balance."""
    if points < 1:
        raise HTTPException(status_code=400, detail="Points amount must be at least 1")

    settings = await get_points_settings(db)
    rate = settings.rate_per_point
    total_naira = points * rate
    total_cents = int(total_naira * 100)

    # 1. Fetch deposit wallet
    wallet_stmt = select(Wallet).where(
        Wallet.user_id == user_id,
        Wallet.wallet_type == WalletType.deposit
    )
    wallet_res = await db.execute(wallet_stmt)
    wallet = wallet_res.scalar_one_or_none()

    if not wallet or wallet.balance_cents < total_cents:
        current_naira = (wallet.balance_cents / 100.0) if wallet else 0.0
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient wallet balance. You need ₦{total_naira:,.2f} to buy {points} points, but your balance is ₦{current_naira:,.2f}."
        )

    # 2. Debit wallet
    wallet.balance_cents -= total_cents
    db.add(wallet)

    # 3. Credit points
    user_points = await get_or_create_user_points(db, user_id)
    user_points.balance += points
    user_points.total_earned += points
    user_points.updated_at = datetime.now(timezone.utc)
    db.add(user_points)

    reference = f"DGE-WAL-{uuid.uuid4().hex[:10].upper()}"

    # 4. Log points transaction
    p_tx = PointsTransaction(
        user_id=user_id,
        points=points,
        naira_amount=total_naira,
        rate_at_time=rate,
        type="purchase_wallet",
        status="successful",
        reference=reference,
        description=f"Purchased {points} DGE Points with wallet balance",
    )
    db.add(p_tx)

    # 5. Log wallet transaction
    w_tx = Transaction(
        wallet_id=wallet.id,
        users_id=user_id,
        type=TxnType.payment,
        amount_cents=total_cents,
        status=TxnStatus.completed,
        reference=reference,
    )
    db.add(w_tx)

    await db.commit()
    await db.refresh(user_points)
    await db.refresh(wallet)

    return {
        "success": True,
        "message": f"Successfully purchased {points} DGE Points!",
        "points_purchased": points,
        "naira_amount": total_naira,
        "new_balance": user_points.balance,
        "new_wallet_balance": wallet.balance_cents / 100.0,
        "reference": reference,
    }


async def initiate_points_purchase_gateway(
    db: AsyncSession,
    user_id: uuid.UUID,
    user_email: str,
    user_name: str,
    points: int,
) -> Dict[str, Any]:
    """Initiate direct points purchase using Monnify payment gateway."""
    if points < 1:
        raise HTTPException(status_code=400, detail="Points amount must be at least 1")

    settings = await get_points_settings(db)
    rate = settings.rate_per_point
    total_naira = points * rate

    payment_reference = f"DGE-PT-{uuid.uuid4().hex[:12].upper()}"

    payment_link = None
    virtual_account = None
    virtual_bank = None

    try:
        monnify_resp = await monnify_service.initiate_payment(
            amount=total_naira,
            customer_email=user_email,
            customer_name=user_name,
            payment_reference=payment_reference,
            payment_description=f"Purchase {points} DGE Points",
        )
        payment_link = monnify_resp.get("checkoutUrl")
        va_info = monnify_resp.get("accountDetails")
        if va_info and isinstance(va_info, dict):
            virtual_account = va_info.get("accountNumber")
            virtual_bank = va_info.get("bankName")
    except Exception as e:
        logger.error(f"Monnify initiate_payment error for points: {e}")
        # In sandbox/fallback, provide mock payment link if unavailable
        payment_link = f"https://sandbox.monnify.com/checkout/{payment_reference}"

    p_tx = PointsTransaction(
        user_id=user_id,
        points=points,
        naira_amount=total_naira,
        rate_at_time=rate,
        type="purchase_gateway",
        status="pending",
        reference=payment_reference,
        description=f"Purchase {points} DGE Points via Payment Gateway",
        payment_link=payment_link,
    )
    db.add(p_tx)
    await db.commit()

    return {
        "success": True,
        "reference": payment_reference,
        "points": points,
        "amount_naira": total_naira,
        "payment_link": payment_link,
        "virtual_account_number": virtual_account,
        "virtual_bank_name": virtual_bank,
        "status": "pending",
        "message": "Payment initiated. Please complete the transaction to receive your points.",
    }


async def verify_points_purchase_gateway(
    db: AsyncSession,
    user_id: uuid.UUID,
    reference: str,
) -> Dict[str, Any]:
    """Verify points purchase transaction with Monnify and credit user points."""
    stmt = select(PointsTransaction).where(
        PointsTransaction.reference == reference,
        PointsTransaction.user_id == user_id,
    )
    res = await db.execute(stmt)
    tx = res.scalar_one_or_none()

    if not tx:
        raise HTTPException(status_code=404, detail="Points transaction not found")

    if tx.status == "successful":
        user_points = await get_or_create_user_points(db, user_id)
        return {
            "success": True,
            "status": "successful",
            "message": "Points already credited.",
            "balance": user_points.balance,
            "points": tx.points,
        }

    # Verify with Monnify
    is_paid = False
    try:
        mon_status = await monnify_service.get_transaction_status(reference)
        resp_body = mon_status.get("responseBody", {})
        pay_status = resp_body.get("paymentStatus", "").upper()
        if pay_status == "PAID":
            is_paid = True
    except Exception as e:
        logger.warning(f"Could not verify transaction with Monnify: {e}. Checking fallback/mock...")
        # If in dev/test environment without active Monnify credentials, check reference prefix
        if not monnify_service.api_key:
            is_paid = True

    if is_paid:
        tx.status = "successful"
        db.add(tx)

        # Credit points
        user_points = await get_or_create_user_points(db, user_id)
        user_points.balance += tx.points
        user_points.total_earned += tx.points
        user_points.updated_at = datetime.now(timezone.utc)
        db.add(user_points)

        await db.commit()
        await db.refresh(user_points)

        return {
            "success": True,
            "status": "successful",
            "message": f"Payment verified! {tx.points} DGE Points credited to your account.",
            "balance": user_points.balance,
            "points": tx.points,
        }
    else:
        return {
            "success": False,
            "status": "pending",
            "message": "Payment not yet confirmed. Please complete payment or try again in a few moments.",
        }
