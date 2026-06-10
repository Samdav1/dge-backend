"""
app/api/v1/payments.py
User-facing payment endpoints: deposits, withdrawals, bank accounts, banks list.
"""
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlmodel.ext.asyncio.session import AsyncSession

from app.db.session import get_session
from app.dependencies.auth import get_current_user
from app.schemas.user import UserRead
from app.schemas.payment import (
    DepositInitiateRequest, DepositInitiateResponse, DepositRead,
    WithdrawalRequestCreate, WithdrawalRequestRead,
    BankAccountCreate, BankAccountRead, BankAccountVerifyRequest, BankAccountVerifyResponse,
)
from app.services import payment_service
from app.services.monnify_service import monnify_service
from app.models.payment_request import DepositRequest, WithdrawalRequest, UserBankAccount
from sqlmodel import select

router = APIRouter()


# ─── Banks List ───────────────────────────────────────────────────────────────

@router.get("/banks", summary="List supported Nigerian banks")
async def list_banks():
    """Return the static list of NGN banks with their codes."""
    return {"banks": monnify_service.get_banks_list()}


# ─── Bank Accounts ─────────────────────────────────────────────────────────────

@router.post("/bank-account/verify", response_model=BankAccountVerifyResponse, summary="Verify a bank account number")
async def verify_bank_account(
    payload: BankAccountVerifyRequest,
    credentials: UserRead = Depends(get_current_user),
):
    """Resolve account number → account name via Monnify name enquiry."""
    try:
        result = await monnify_service.verify_bank_account(
            account_number=payload.account_number,
            bank_code=payload.bank_code,
        )
        return BankAccountVerifyResponse(
            account_number=result.get("accountNumber", payload.account_number),
            account_name=result.get("accountName", ""),
            bank_code=payload.bank_code,
            bank_name=result.get("bankName", ""),
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Bank verification failed: {str(e)}")


@router.post("/bank-account", response_model=BankAccountRead, summary="Save a verified bank account")
async def add_bank_account(
    payload: BankAccountCreate,
    db: AsyncSession = Depends(get_session),
    credentials: UserRead = Depends(get_current_user),
):
    acct = await payment_service.verify_and_save_bank_account(db, credentials.id, payload)
    return BankAccountRead.model_validate(acct)


@router.get("/bank-account", response_model=List[BankAccountRead], summary="Get saved bank accounts")
async def get_bank_accounts(
    db: AsyncSession = Depends(get_session),
    credentials: UserRead = Depends(get_current_user),
):
    accounts = await payment_service.get_user_bank_accounts(db, credentials.id)
    return [BankAccountRead.model_validate(a) for a in accounts]


@router.delete("/bank-account/{account_id}", summary="Remove a saved bank account")
async def delete_bank_account(
    account_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    credentials: UserRead = Depends(get_current_user),
):
    await payment_service.delete_bank_account(db, account_id, credentials.id)
    return {"message": "Bank account removed"}


# ─── Deposits ─────────────────────────────────────────────────────────────────

@router.post("/deposit/initiate", response_model=DepositInitiateResponse, summary="Initiate a wallet deposit")
async def initiate_deposit(
    payload: DepositInitiateRequest,
    db: AsyncSession = Depends(get_session),
    credentials: UserRead = Depends(get_current_user),
):
    """
    Creates a DepositRequest and returns a Monnify checkout link.
    The user completes payment on Monnify's hosted page; the webhook then
    credits the wallet (or holds for admin screening).
    """
    # Try to get user's name from profile (fallback to username)
    user_name = getattr(credentials, "username", str(credentials.id))

    deposit = await payment_service.initiate_deposit(
        db=db,
        user_id=credentials.id,
        amount_naira=payload.amount,
        user_email=credentials.email,
        user_name=user_name,
    )

    screen_msg = (
        "Payment initiated. Complete the payment via the link provided. "
        "Your wallet will be credited after admin review."
        if deposit.status.value == "failed"
        else "Payment initiated. Complete payment via the link. Your wallet will be credited automatically."
    )

    return DepositInitiateResponse(
        deposit_id=deposit.id,
        amount_naira=payload.amount,
        monnify_reference=deposit.monnify_reference or "",
        payment_link=deposit.payment_link,
        virtual_account_number=deposit.virtual_account_number,
        virtual_bank_name=deposit.virtual_bank_name,
        status=deposit.status,
        message=screen_msg,
    )


@router.post("/deposit/webhook", summary="Monnify deposit webhook (internal)")
async def deposit_webhook(
    request: Request,
    db: AsyncSession = Depends(get_session),
    monnify_signature: Optional[str] = Header(None, alias="monnify-signature"),
):
    """
    Receives Monnify payment notifications.
    Verifies HMAC signature then processes the deposit.
    """
    raw_body = await request.body()

    # Signature verification (skip in dev if secret not set)
    if monnify_service.secret_key:
        if not monnify_signature:
            raise HTTPException(status_code=400, detail="Missing Monnify-Signature header")
        if not monnify_service.verify_webhook_signature(raw_body, monnify_signature):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    result = await payment_service.handle_deposit_webhook(db, payload)
    return result


@router.get("/deposit/history", response_model=List[DepositRead], summary="Get deposit history")
async def get_deposit_history(
    db: AsyncSession = Depends(get_session),
    credentials: UserRead = Depends(get_current_user),
):
    stmt = select(DepositRequest).where(
        DepositRequest.user_id == credentials.id
    ).order_by(DepositRequest.created_at.desc())
    res = await db.execute(stmt)
    deposits = res.scalars().all()
    return [DepositRead.model_validate(d) for d in deposits]


# ─── Withdrawals ─────────────────────────────────────────────────────────────

@router.post("/withdrawal/request", response_model=WithdrawalRequestRead, summary="Request a withdrawal")
async def request_withdrawal(
    payload: WithdrawalRequestCreate,
    db: AsyncSession = Depends(get_session),
    credentials: UserRead = Depends(get_current_user),
):
    """
    Submit a withdrawal request from the user's earnings wallet.
    If auto_approve_withdrawals is enabled by admin, the transfer is triggered immediately.
    Otherwise it goes into the admin approval queue.
    """
    withdrawal = await payment_service.initiate_withdrawal(db, credentials.id, payload)
    return WithdrawalRequestRead.model_validate(withdrawal)


@router.get("/withdrawal/history", response_model=List[WithdrawalRequestRead], summary="Get withdrawal history")
async def get_withdrawal_history(
    db: AsyncSession = Depends(get_session),
    credentials: UserRead = Depends(get_current_user),
):
    stmt = select(WithdrawalRequest).where(
        WithdrawalRequest.user_id == credentials.id
    ).order_by(WithdrawalRequest.created_at.desc())
    res = await db.execute(stmt)
    withdrawals = res.scalars().all()
    return [WithdrawalRequestRead.model_validate(w) for w in withdrawals]
