"""
app/api/v1/points.py
User-facing and general DGE Points endpoints: summary, rates, purchasing via wallet and gateway.
"""
from typing import Optional, List, Dict, Any
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlmodel.ext.asyncio.session import AsyncSession

from app.db.session import get_session
from app.dependencies.auth import get_current_user
from app.schemas.user import UserRead
from app.services import points_service

router = APIRouter(tags=["DGE Points"])


class BuyPointsRequest(BaseModel):
    points: int = Field(..., ge=1, description="Number of DGE Points to buy")


class SpendPointsRequest(BaseModel):
    points: int = Field(..., ge=1, description="Number of DGE Points to spend")
    description: str = Field(..., description="Reason for points deduction")
    context: Optional[str] = Field(None, description="Domain context (e.g., marketplace, posted_job, driving)")


class RecordFailedNegotiationRequest(BaseModel):
    context: str = Field("general", description="Context: marketplace, posted_job, or driving")


@router.get("/settings", summary="Get public DGE Points settings & rate")
async def get_points_settings(db: AsyncSession = Depends(get_session)):
    """Returns current exchange rate per point and signup bonus."""
    settings = await points_service.get_points_settings(db)
    return {
        "rate_per_point": settings.rate_per_point,
        "signup_bonus_points": settings.signup_bonus_points,
        "min_purchase_points": settings.min_purchase_points,
        "updated_at": settings.updated_at.isoformat() if settings.updated_at else None,
    }


@router.get("/me", summary="Get current user's DGE Points and recent transactions")
async def get_my_points(
    db: AsyncSession = Depends(get_session),
    credentials: UserRead = Depends(get_current_user),
):
    """Returns user's points balance, equivalent in Naira, and recent transaction history."""
    summary = await points_service.get_user_points_summary(db, credentials.id)
    transactions = await points_service.get_user_points_transactions(db, credentials.id, limit=30)
    
    return {
        **summary,
        "transactions": [
            {
                "id": str(t.id),
                "points": t.points,
                "naira_amount": t.naira_amount,
                "rate_at_time": t.rate_at_time,
                "type": t.type,
                "status": t.status,
                "reference": t.reference,
                "description": t.description,
                "payment_link": t.payment_link,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in transactions
        ],
    }


@router.post("/buy/wallet", summary="Buy DGE Points using deposit wallet balance")
async def buy_points_wallet(
    payload: BuyPointsRequest,
    db: AsyncSession = Depends(get_session),
    credentials: UserRead = Depends(get_current_user),
):
    """Deducts cost in Naira from user's deposit wallet and credits points immediately."""
    result = await points_service.buy_points_with_wallet(
        db=db,
        user_id=credentials.id,
        points=payload.points,
    )
    return result


@router.post("/buy/initiate", summary="Initiate direct points purchase via Monnify payment gateway")
async def buy_points_gateway(
    payload: BuyPointsRequest,
    db: AsyncSession = Depends(get_session),
    credentials: UserRead = Depends(get_current_user),
):
    """Creates a payment request and returns Monnify checkout link."""
    user_name = getattr(credentials, "username", str(credentials.id))
    result = await points_service.initiate_points_purchase_gateway(
        db=db,
        user_id=credentials.id,
        user_email=credentials.email,
        user_name=user_name,
        points=payload.points,
    )
    return result


@router.post("/buy/verify/{reference}", summary="Verify direct gateway payment and credit points")
async def verify_points_payment(
    reference: str,
    db: AsyncSession = Depends(get_session),
    credentials: UserRead = Depends(get_current_user),
):
    """Verify transaction with Monnify and credit DGE points upon confirmation."""
    result = await points_service.verify_points_purchase_gateway(
        db=db,
        user_id=credentials.id,
        reference=reference,
    )
    return result


@router.post("/spend", summary="Deduct DGE Points for usage, negotiation or completed services")
async def spend_points(
    payload: SpendPointsRequest,
    db: AsyncSession = Depends(get_session),
    credentials: UserRead = Depends(get_current_user),
):
    """Deduct points from the current user's balance and record a spend transaction."""
    result = await points_service.deduct_user_points(
        db=db,
        user_id=credentials.id,
        points=payload.points,
        description=payload.description,
        context=payload.context,
    )
    return result


@router.post("/record-failed-negotiation", summary="Record an unagreed negotiation attempt for fair-use policy")
async def record_failed_negotiation(
    payload: RecordFailedNegotiationRequest,
    db: AsyncSession = Depends(get_session),
    credentials: UserRead = Depends(get_current_user),
):
    """Record a failed negotiation attempt. After 3 attempts without agreement, 1 point is deducted."""
    result = await points_service.record_failed_negotiation(
        db=db,
        user_id=credentials.id,
        context=payload.context,
    )
    return result
