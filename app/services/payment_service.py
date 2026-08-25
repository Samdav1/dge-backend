"""
Payment business logic service.
Handles deposit & withdrawal lifecycle, admin settings, and Monnify integration.
"""
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException
from sqlmodel import select, func
from sqlmodel.ext.asyncio.session import AsyncSession
from app.models.user import Users


from app.models.payment_request import (
    DepositRequest, DepositStatus,
    WithdrawalRequest, WithdrawalStatus,
    UserBankAccount,
)
from app.models.admin import AdminPaymentSettings
from app.models.wallet import Wallet, WalletType
from app.models.transactions import Transaction, TxnType, TxnStatus
from app.schemas.payment import (
    BankAccountCreate, DepositInitiateRequest,
    WithdrawalRequestCreate,
)
from app.services.monnify_service import monnify_service
from app.services.email_notification_service import NotificationService

logger = logging.getLogger(__name__)


# ─── Admin Payment Settings ───────────────────────────────────────────────────

async def _validate_admin_id(db: AsyncSession, admin_id: Optional[uuid.UUID]) -> Optional[uuid.UUID]:
    """Verify if admin_id exists in superadmin table; return a valid superadmin ID or None."""
    from app.models.admin import SuperAdmin
    if admin_id:
        stmt = select(SuperAdmin).where(SuperAdmin.id == admin_id)
        res = await db.execute(stmt)
        if res.scalar_one_or_none():
            return admin_id
    # Fallback: return the first superadmin record ID if any exists
    stmt_first = select(SuperAdmin.id).limit(1)
    res_first = await db.execute(stmt_first)
    return res_first.scalar_one_or_none()


async def get_payment_settings(db: AsyncSession) -> AdminPaymentSettings:
    """Return the single settings row, creating it with defaults if absent."""
    stmt = select(AdminPaymentSettings).where(AdminPaymentSettings.id == 1)
    res = await db.execute(stmt)
    settings = res.scalar_one_or_none()
    if not settings:
        settings = AdminPaymentSettings(id=1)
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
    return settings


async def update_payment_settings(
    db: AsyncSession,
    auto_approve_withdrawals: Optional[bool],
    screen_deposits: Optional[bool],
    admin_id: Optional[uuid.UUID] = None,
) -> AdminPaymentSettings:
    settings = await get_payment_settings(db)
    if auto_approve_withdrawals is not None:
        settings.auto_approve_withdrawals = auto_approve_withdrawals
    if screen_deposits is not None:
        settings.screen_deposits = screen_deposits
    settings.updated_at = datetime.now(timezone.utc)
    if admin_id:
        settings.updated_by_admin_id = await _validate_admin_id(db, admin_id)
    db.add(settings)
    await db.commit()
    await db.refresh(settings)
    return settings


# ─── Bank Accounts ────────────────────────────────────────────────────────────

async def verify_and_save_bank_account(
    db: AsyncSession,
    user_id: uuid.UUID,
    payload: BankAccountCreate,
) -> UserBankAccount:
    """Save a pre-verified bank account for a user. Optionally make it default."""
    if payload.is_default:
        # Unset any existing default
        stmt = select(UserBankAccount).where(UserBankAccount.user_id == user_id)
        res = await db.execute(stmt)
        for acct in res.scalars().all():
            acct.is_default = False
            db.add(acct)

    acct = UserBankAccount(
        user_id=user_id,
        account_number=payload.account_number,
        account_name=payload.account_name,
        bank_code=payload.bank_code,
        bank_name=payload.bank_name,
        is_default=payload.is_default,
    )
    db.add(acct)
    await db.commit()
    await db.refresh(acct)
    return acct


async def get_user_bank_accounts(db: AsyncSession, user_id: uuid.UUID) -> list[UserBankAccount]:
    stmt = select(UserBankAccount).where(UserBankAccount.user_id == user_id)
    res = await db.execute(stmt)
    return res.scalars().all()


async def delete_bank_account(db: AsyncSession, account_id: uuid.UUID, user_id: uuid.UUID) -> None:
    stmt = select(UserBankAccount).where(
        UserBankAccount.id == account_id,
        UserBankAccount.user_id == user_id,
    )
    res = await db.execute(stmt)
    acct = res.scalar_one_or_none()
    if not acct:
        raise HTTPException(status_code=404, detail="Bank account not found")
    await db.delete(acct)
    await db.commit()


# ─── Deposits ─────────────────────────────────────────────────────────────────

async def initiate_deposit(
    db: AsyncSession,
    user_id: uuid.UUID,
    amount_naira: float,
    user_email: str,
    user_name: str,
) -> DepositRequest:
    """
    Create a DepositRequest and get a Monnify payment link.
    """
    if amount_naira < 100:
        raise HTTPException(status_code=400, detail="Minimum deposit is ₦100")

    # Get user's deposit wallet
    wallet_stmt = select(Wallet).where(
        Wallet.user_id == user_id, Wallet.wallet_type == WalletType.deposit
    )
    wallet_res = await db.execute(wallet_stmt)
    wallet = wallet_res.scalar_one_or_none()
    if not wallet:
        raise HTTPException(status_code=404, detail="Deposit wallet not found. Please create your wallet first.")

    amount_cents = int(amount_naira * 100)
    payment_reference = f"DGE-DEP-{uuid.uuid4().hex[:12].upper()}"

    deposit = DepositRequest(
        user_id=user_id,
        wallet_id=wallet.id,
        amount_cents=amount_cents,
        currency="NGN",
        monnify_reference=payment_reference,
        status=DepositStatus.pending,
    )

    try:
        monnify_resp = await monnify_service.initiate_payment(
            amount=amount_naira,
            customer_email=user_email,
            customer_name=user_name,
            payment_reference=payment_reference,
            payment_description="DGE Wallet Funding",
        )
        deposit.payment_link = monnify_resp.get("checkoutUrl")
        deposit.monnify_transaction_ref = monnify_resp.get("transactionReference")
    except Exception as e:
        logger.error(f"Monnify initiate_payment error: {e}")
        # Still save the deposit request even if Monnify call fails — admin can retry
        deposit.status = DepositStatus.failed

    db.add(deposit)
    await db.commit()
    await db.refresh(deposit)
    return deposit


async def handle_deposit_webhook(db: AsyncSession, payload: dict) -> dict:
    """
    Process an incoming Monnify deposit webhook.
    - If screen_deposits=False → credit wallet immediately.
    - If screen_deposits=True → set status to screened_pending (admin must approve).
    """
    event_type = payload.get("eventType", "")
    txn_body = payload.get("eventData", {})
    payment_reference = txn_body.get("paymentReference") or txn_body.get("merchantPaymentReference", "")
    paid_status = txn_body.get("paymentStatus", "")

    # Only process successful payments
    if paid_status not in ("PAID", "OVERPAID"):
        return {"processed": False, "reason": f"Skipping status: {paid_status}"}

    stmt = select(DepositRequest).where(DepositRequest.monnify_reference == payment_reference)
    res = await db.execute(stmt)
    deposit = res.scalar_one_or_none()

    if not deposit:
        logger.warning(f"Deposit with reference {payment_reference} not found")
        return {"processed": False, "reason": "Deposit not found"}

    if deposit.status in (DepositStatus.approved, DepositStatus.confirmed):
        return {"processed": False, "reason": "Already processed"}

    deposit.metadata_json = json.dumps(payload)
    deposit.updated_at = datetime.now(timezone.utc)

    settings = await get_payment_settings(db)

    if settings.screen_deposits:
        deposit.status = DepositStatus.screened_pending
        db.add(deposit)
        await db.commit()
        return {"processed": True, "action": "held_for_review"}
    else:
        deposit.status = DepositStatus.confirmed
        db.add(deposit)
        await _credit_wallet_for_deposit(db, deposit)
        return {"processed": True, "action": "credited"}


async def _credit_wallet_for_deposit(db: AsyncSession, deposit: DepositRequest) -> None:
    """Credit the user's deposit wallet and create a Transaction record."""
    wallet_stmt = select(Wallet).where(Wallet.id == deposit.wallet_id)
    wallet_res = await db.execute(wallet_stmt)
    wallet = wallet_res.scalar_one_or_none()
    if not wallet:
        logger.error(f"Wallet {deposit.wallet_id} not found for deposit {deposit.id}")
        return

    from app.services.fee_service import fee_service
    fee_cents, net_cents = await fee_service.apply_fee(
        db=db,
        event_type="deposit",
        user_id=deposit.user_id,
        gross_amount_cents=deposit.amount_cents,
        reference=deposit.monnify_reference
    )

    wallet.balance_cents += net_cents
    db.add(wallet)

    txn = Transaction(
        wallet_id=wallet.id,
        users_id=deposit.user_id,
        type=TxnType.deposit,
        amount_cents=net_cents,
        status=TxnStatus.completed,
        reference=deposit.monnify_reference,
    )
    db.add(txn)
    deposit.status = DepositStatus.approved
    db.add(deposit)
    
    # Process referral bonus
    user_stmt = select(Users).where(Users.id == deposit.user_id)
    user_res = await db.execute(user_stmt)
    user = user_res.scalar_one_or_none()
    
    if user and user.referred_by_id:
        # Check if this is the first completed deposit
        deposit_count_stmt = select(func.count(Transaction.id)).where(
            Transaction.users_id == deposit.user_id,
            Transaction.type == TxnType.deposit,
            Transaction.status == TxnStatus.completed
        )
        deposit_count_res = await db.execute(deposit_count_stmt)
        completed_deposits = deposit_count_res.scalar_one_or_none() or 0
        
        # Since we just added the current txn (but haven't committed), it might not be counted by func.count if we don't flush, 
        # but just in case, we check if completed_deposits == 0 (meaning no *previous* deposits were committed)
        if completed_deposits == 0:
            bonus_cents = int(deposit.amount_cents * 0.05)
            
            referrer_wallet_stmt = select(Wallet).where(
                Wallet.user_id == user.referred_by_id,
                Wallet.wallet_type == WalletType.earnings
            )
            referrer_wallet_res = await db.execute(referrer_wallet_stmt)
            referrer_wallet = referrer_wallet_res.scalar_one_or_none()
            
            if referrer_wallet:
                referrer_wallet.balance_cents += bonus_cents
                db.add(referrer_wallet)
                
                bonus_txn = Transaction(
                    wallet_id=referrer_wallet.id,
                    users_id=user.referred_by_id,
                    type=TxnType.deposit,
                    amount_cents=bonus_cents,
                    status=TxnStatus.completed,
                    reference=f"REF-BONUS-{deposit.id}",
                )
                db.add(bonus_txn)

    await db.commit()
    
    # Send Deposit Email
    if user:
        try:
            NotificationService().send_deposit_success_mail(
                user=user,
                amount_cents=deposit.amount_cents,
                reference=deposit.monnify_reference,
                date_str=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            )
        except Exception as e:
            logger.error(f"Failed to send deposit email: {e}")


async def verify_deposit(db: AsyncSession, deposit_id: uuid.UUID, user_id: uuid.UUID) -> dict:
    """
    User-triggered deposit verification.
    Polls Monnify's transaction status API to check if the payment was completed,
    then credits the wallet if it was. This is the primary crediting path since
    Monnify webhooks may not reach the server on cPanel deployments.
    """
    stmt = select(DepositRequest).where(
        DepositRequest.id == deposit_id,
        DepositRequest.user_id == user_id,
    )
    res = await db.execute(stmt)
    deposit = res.scalar_one_or_none()

    if not deposit:
        raise HTTPException(status_code=404, detail="Deposit not found")

    # Already credited — nothing to do
    if deposit.status in (DepositStatus.approved, DepositStatus.confirmed):
        return {"verified": True, "status": deposit.status.value, "message": "Deposit already credited"}

    if not deposit.monnify_reference:
        raise HTTPException(status_code=400, detail="No Monnify reference for this deposit")

    # Query Monnify for the real payment status
    try:
        txn_data = await monnify_service.get_transaction_status(deposit.monnify_reference)
    except Exception as e:
        logger.error(f"Monnify verification failed for {deposit.monnify_reference}: {e}")
        raise HTTPException(status_code=502, detail=f"Could not verify with Monnify: {str(e)}")

    payment_status = txn_data.get("paymentStatus", "")
    logger.info(f"Monnify verification for {deposit.monnify_reference}: paymentStatus={payment_status}")

    if payment_status not in ("PAID", "OVERPAID"):
        return {
            "verified": False,
            "status": payment_status,
            "message": f"Payment not yet completed (status: {payment_status})",
        }

    # Payment confirmed — credit the wallet
    deposit.metadata_json = json.dumps(txn_data)
    deposit.updated_at = datetime.now(timezone.utc)

    settings = await get_payment_settings(db)

    if settings.screen_deposits:
        deposit.status = DepositStatus.screened_pending
        db.add(deposit)
        await db.commit()
        return {
            "verified": True,
            "status": "screened_pending",
            "message": "Payment confirmed. Your deposit is pending admin review.",
        }
    else:
        deposit.status = DepositStatus.confirmed
        db.add(deposit)
        await _credit_wallet_for_deposit(db, deposit)
        return {
            "verified": True,
            "status": "approved",
            "message": "Payment confirmed! Your wallet has been credited.",
        }


async def admin_approve_deposit(
    db: AsyncSession,
    deposit_id: uuid.UUID,
    admin_id: Optional[uuid.UUID] = None,
) -> DepositRequest:
    """Admin approves a screened_pending deposit → credits wallet."""
    stmt = select(DepositRequest).where(DepositRequest.id == deposit_id)
    res = await db.execute(stmt)
    deposit = res.scalar_one_or_none()
    if not deposit:
        raise HTTPException(status_code=404, detail="Deposit not found")
    if deposit.status != DepositStatus.screened_pending:
        raise HTTPException(status_code=400, detail=f"Deposit is not pending review (status: {deposit.status.value})")

    deposit.approved_by_admin_id = await _validate_admin_id(db, admin_id)
    await _credit_wallet_for_deposit(db, deposit)
    await db.refresh(deposit)
    return deposit


# ─── Withdrawals ─────────────────────────────────────────────────────────────

async def initiate_withdrawal(
    db: AsyncSession,
    user_id: uuid.UUID,
    payload: WithdrawalRequestCreate,
) -> WithdrawalRequest:
    """
    Submit a withdrawal request.
    - Validates sufficient balance in the EARNINGS wallet.
    - If auto_approve_withdrawals=True → triggers Monnify transfer immediately.
    - Otherwise → queues for admin approval.
    """
    if payload.amount < 100:
        raise HTTPException(status_code=400, detail="Minimum withdrawal is ₦100")

    amount_cents = int(payload.amount * 100)

    # Check earnings wallet balance (withdrawals come from earnings)
    wallet_stmt = select(Wallet).where(
        Wallet.user_id == user_id, Wallet.wallet_type == WalletType.earnings
    )
    wallet_res = await db.execute(wallet_stmt)
    wallet = wallet_res.scalar_one_or_none()
    if not wallet:
        raise HTTPException(status_code=404, detail="Earnings wallet not found")
    if wallet.balance_cents < amount_cents:
        raise HTTPException(status_code=400, detail="Insufficient earnings balance")

    # Validate bank account belongs to user
    bank_stmt = select(UserBankAccount).where(
        UserBankAccount.id == payload.bank_account_id,
        UserBankAccount.user_id == user_id,
    )
    bank_res = await db.execute(bank_stmt)
    bank_account = bank_res.scalar_one_or_none()
    if not bank_account:
        raise HTTPException(status_code=404, detail="Bank account not found")

    withdrawal = WithdrawalRequest(
        user_id=user_id,
        wallet_id=wallet.id,
        bank_account_id=bank_account.id,
        amount_cents=amount_cents,
        currency="NGN",
        status=WithdrawalStatus.pending,
    )
    db.add(withdrawal)
    await db.commit()
    await db.refresh(withdrawal)

    settings = await get_payment_settings(db)
    if settings.auto_approve_withdrawals:
        # Auto-approve: debit wallet immediately and trigger Monnify transfer
        withdrawal = await _process_withdrawal_transfer(db, withdrawal, bank_account, wallet)
    
    # Send email notification
    user_stmt = select(Users).where(Users.id == user_id)
    user_res = await db.execute(user_stmt)
    user = user_res.scalar_one_or_none()
    
    if user:
        try:
            NotificationService().send_withdrawal_status_mail(
                user=user,
                status=withdrawal.status.value,
                amount_cents=amount_cents,
                bank_name=bank_account.bank_name,
                account_number=bank_account.account_number,
                reference=withdrawal.monnify_reference
            )
        except Exception as e:
            logger.error(f"Failed to send withdrawal email: {e}")

    return withdrawal


async def _process_withdrawal_transfer(
    db: AsyncSession,
    withdrawal: WithdrawalRequest,
    bank_account: UserBankAccount,
    wallet: Wallet,
) -> WithdrawalRequest:
    """Debit wallet and trigger Monnify single disbursement."""
    reference = f"DGE-WDR-{uuid.uuid4().hex[:12].upper()}"

    from app.services.fee_service import fee_service
    config = await fee_service.get_fee_config(db)
    fee_cents = 0
    if config.withdrawal_fee_enabled:
        fee_cents = fee_service.calculate_fee(
            withdrawal.amount_cents,
            config.withdrawal_fee_type,
            config.withdrawal_fee_value
        )
    net_cents = withdrawal.amount_cents - fee_cents
    amount_naira = net_cents / 100

    try:
        resp = await monnify_service.initiate_single_transfer(
            amount=amount_naira,
            reference=reference,
            narration="DGE Earnings Withdrawal",
            destination_bank_code=bank_account.bank_code,
            destination_account_number=bank_account.account_number,
            destination_account_name=bank_account.account_name,
        )
        monnify_status = resp.get("status", "")
        withdrawal.monnify_reference = reference
        withdrawal.status = (
            WithdrawalStatus.completed if monnify_status == "SUCCESS"
            else WithdrawalStatus.processing
        )
    except Exception as e:
        logger.error(f"Monnify transfer error for withdrawal {withdrawal.id}: {e}")
        withdrawal.status = WithdrawalStatus.failed

    # Debit wallet regardless (funds reserved/withdrawn from balance)
    wallet.balance_cents -= withdrawal.amount_cents
    db.add(wallet)

    txn = Transaction(
        wallet_id=wallet.id,
        users_id=withdrawal.user_id,
        type=TxnType.withdrawal,
        amount_cents=withdrawal.amount_cents,
        status=TxnStatus.completed if withdrawal.status == WithdrawalStatus.completed else TxnStatus.pending,
        reference=reference,
    )
    db.add(txn)

    # Only log revenue if the transfer didn't fail
    if withdrawal.status in (WithdrawalStatus.completed, WithdrawalStatus.processing) and fee_cents > 0:
        from app.models.admin import PlatformRevenueLog
        log = PlatformRevenueLog(
            event_type="withdrawal",
            user_id=withdrawal.user_id,
            gross_amount_cents=withdrawal.amount_cents,
            fee_amount_cents=fee_cents,
            fee_type=config.withdrawal_fee_type,
            fee_value=config.withdrawal_fee_value,
            reference=str(withdrawal.id)
        )
        db.add(log)

    withdrawal.updated_at = datetime.now(timezone.utc)
    db.add(withdrawal)
    await db.commit()
    await db.refresh(withdrawal)
    return withdrawal


async def admin_approve_withdrawal(
    db: AsyncSession,
    withdrawal_id: uuid.UUID,
    admin_id: Optional[uuid.UUID] = None,
) -> WithdrawalRequest:
    """Admin approves a pending withdrawal → triggers Monnify transfer."""
    stmt = select(WithdrawalRequest).where(WithdrawalRequest.id == withdrawal_id)
    res = await db.execute(stmt)
    withdrawal = res.scalar_one_or_none()
    if not withdrawal:
        raise HTTPException(status_code=404, detail="Withdrawal request not found")
    if withdrawal.status != WithdrawalStatus.pending:
        raise HTTPException(status_code=400, detail=f"Cannot approve withdrawal in status: {withdrawal.status.value}")

    # Fetch bank account
    bank_stmt = select(UserBankAccount).where(UserBankAccount.id == withdrawal.bank_account_id)
    bank_res = await db.execute(bank_stmt)
    bank_account = bank_res.scalar_one_or_none()
    if not bank_account:
        raise HTTPException(status_code=404, detail="Bank account not found")

    # Fetch wallet
    wallet_stmt = select(Wallet).where(Wallet.id == withdrawal.wallet_id)
    wallet_res = await db.execute(wallet_stmt)
    wallet = wallet_res.scalar_one_or_none()
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")

    if wallet.balance_cents < withdrawal.amount_cents:
        raise HTTPException(status_code=400, detail="Insufficient wallet balance at time of approval")

    withdrawal.approved_by_admin_id = await _validate_admin_id(db, admin_id)
    withdrawal.reviewed_at = datetime.now(timezone.utc)
    withdrawal = await _process_withdrawal_transfer(db, withdrawal, bank_account, wallet)
    
    # Send email notification
    user_stmt = select(Users).where(Users.id == withdrawal.user_id)
    user_res = await db.execute(user_stmt)
    user = user_res.scalar_one_or_none()
    if user:
        try:
            NotificationService().send_withdrawal_status_mail(
                user=user,
                status=withdrawal.status.value,
                amount_cents=withdrawal.amount_cents,
                bank_name=bank_account.bank_name,
                account_number=bank_account.account_number,
                reference=withdrawal.monnify_reference
            )
        except Exception as e:
            logger.error(f"Failed to send withdrawal approval email: {e}")
            
    return withdrawal


async def admin_reject_withdrawal(
    db: AsyncSession,
    withdrawal_id: uuid.UUID,
    admin_id: Optional[uuid.UUID] = None,
    reason: str = "No reason provided",
) -> WithdrawalRequest:
    """Admin rejects a pending withdrawal."""
    stmt = select(WithdrawalRequest).where(WithdrawalRequest.id == withdrawal_id)
    res = await db.execute(stmt)
    withdrawal = res.scalar_one_or_none()
    if not withdrawal:
        raise HTTPException(status_code=404, detail="Withdrawal request not found")
    if withdrawal.status != WithdrawalStatus.pending:
        raise HTTPException(status_code=400, detail=f"Cannot reject withdrawal in status: {withdrawal.status.value}")

    withdrawal.status = WithdrawalStatus.rejected
    withdrawal.rejection_reason = reason
    withdrawal.approved_by_admin_id = await _validate_admin_id(db, admin_id)
    withdrawal.reviewed_at = datetime.now(timezone.utc)
    withdrawal.updated_at = datetime.now(timezone.utc)
    db.add(withdrawal)
    await db.commit()
    await db.refresh(withdrawal)
    
    # Send email notification
    user_stmt = select(Users).where(Users.id == withdrawal.user_id)
    user_res = await db.execute(user_stmt)
    user = user_res.scalar_one_or_none()
    if user:
        # Need bank info for the email
        bank_stmt = select(UserBankAccount).where(UserBankAccount.id == withdrawal.bank_account_id)
        bank_res = await db.execute(bank_stmt)
        bank_account = bank_res.scalar_one_or_none()
        
        bank_name = bank_account.bank_name if bank_account else "Unknown"
        account_number = bank_account.account_number if bank_account else "Unknown"
        
        try:
            NotificationService().send_withdrawal_status_mail(
                user=user,
                status="rejected",
                amount_cents=withdrawal.amount_cents,
                bank_name=bank_name,
                account_number=account_number,
                reference=withdrawal.monnify_reference,
                rejection_reason=reason
            )
        except Exception as e:
            logger.error(f"Failed to send withdrawal rejection email: {e}")
            
    return withdrawal
