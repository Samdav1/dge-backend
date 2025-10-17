from typing import Optional
from app.services.email_notification_service import NotificationService
from fastapi import HTTPException
from jinja2 import Environment, FileSystemLoader
from sqlalchemy.orm import selectinload
from sqlmodel.ext.asyncio.session import AsyncSession, Select
from sqlalchemy import select as sa_select
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timezone
import uuid
from app.models import Users
from app.repositories.escrow_repo import EscrowRepository
from app.models.escrow import Escrow, EscrowStatus
from app.models.wallet import Wallet
from app.models.price_negotiation import PriceNegotiation
from app.models.transactions import Transaction, TxnType, TxnStatus
from app.repositories.wallet_repo import update_user_wallet_balance_repo, update_user_wallet_balance_repo_ext
from app.schemas.escrow import EscrowCreate
from app.schemas.transactions import TransactionCreate
from app.services.wallet_service import update_user_wallet_service
from app.repositories.transactions_repo import TransactionRepository
from app.workers.tasks.email_service_task import send_email_task

class EscrowService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = EscrowRepository(db)
        self.notifier = NotificationService()

    from sqlalchemy.orm import selectinload

    async def create_escrow(self, user, payload: EscrowCreate) -> Escrow:
        """
        Creates an escrow atomically within a single database transaction.
        """
        query = (
            Select(PriceNegotiation)
            .where(PriceNegotiation.id == payload.payment_negotiation_id)
            .options(
                selectinload(PriceNegotiation.initiator).options(selectinload(Users.wallet)),
                selectinload(PriceNegotiation.receiver).options(selectinload(Users.wallet)),
            )
        )
        result = await self.db.exec(query)
        negotiation = result.scalars().first()

        if not negotiation:
            raise HTTPException(status_code=404, detail="Price negotiation not found")


        initiator = negotiation.initiator
        receiver = negotiation.receiver

        if initiator.id == user.id:
            payer_user = initiator
            payee_user = receiver
        elif receiver.id == user.id:
            payer_user = receiver
            payee_user = initiator
        else:
            raise HTTPException(status_code=403, detail="Authenticated user is not part of this negotiation.")

        payer_wallet = payer_user.wallet[1] if payer_user.wallet else None
        payee_wallet = payee_user.wallet[1] if payee_user.wallet else None

        if not payer_wallet or not payee_wallet:
            raise HTTPException(status_code=404, detail="Payer or payee wallet could not be found.")


        if payer_wallet.user_id != user.id:
            raise HTTPException(status_code=403, detail="You do not own the payer wallet for this negotiation")

        if negotiation.proposed_price_cents != payload.amount_cents:
            raise HTTPException(status_code=400, detail="Payload amount does not match the negotiated amount")

        if payer_wallet.balance_cents < negotiation.proposed_price_cents:
            print('testing', payer_wallet)
            raise HTTPException(status_code=402, detail="Insufficient funds in payer wallet")

        existing_escrow = await self.repo.get_by_negotiation(payload.payment_negotiation_id)
        if existing_escrow:
            raise HTTPException(status_code=409, detail="An escrow already exists for this negotiation")

        try:
            await update_user_wallet_balance_repo_ext(self.db, wallet_type=payer_wallet.wallet_type, amount=-negotiation.proposed_price_cents, credentials=payer_user.id)

            execute_transact = TransactionRepository(db=self.db)
            txn_data = TransactionCreate(
                wallet_id=payer_wallet.id,
                users_id=user.id,
                type=TxnType.withdrawal,
                amount_cents=negotiation.proposed_price_cents,
                status=TxnStatus.completed,
                reference=f"escrow_creation_{negotiation.id}"
            )
            await execute_transact.create_transaction_ext(txn_data)
            self.notifier.send_escrow_creation_debit(payer_user, negotiation)

            new_escrow = Escrow(
                payer_wallet_id=payer_wallet.id,
                payee_wallet_id=payee_wallet.id,
                payment_negotiation_id=negotiation.id,
                amount_cents=negotiation.proposed_price_cents,
                status=EscrowStatus.held
            )
            await self.repo.create_ext(escrow=new_escrow)
            await self.db.commit()

        except Exception as e:
            await self.db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create escrow due to a database error: {str(e)}"
            )

        await self.db.refresh(new_escrow)
        self.notifier.send_escrow_creation_mail(payer_user, payee_user, escrow=new_escrow)

        return new_escrow

    async def release_escrow(self, user, escrow_id: uuid.UUID) -> Escrow:
        """
        Release escrow funds to the payee within a single atomic transaction.
        """
        query = (
            Select(Escrow)
            .where(Escrow.id == escrow_id)
            .options(
                selectinload(Escrow.payee_wallet).options(selectinload(Wallet.user)),
                selectinload(Escrow.payer_wallet).options(selectinload(Wallet.user)),
            )
        )
        result = await self.db.exec(query)
        escrow = result.scalars().first()

        if not escrow:
            raise HTTPException(status_code=404, detail="Escrow not found")

        if escrow.status != EscrowStatus.held:
            raise HTTPException(status_code=400, detail="Only held escrows can be released")

        payee_wallet = escrow.payee_wallet
        payer_wallet = escrow.payer_wallet
        payee_user = payee_wallet.user
        payer_user = payer_wallet.user

        if not payee_wallet or not payer_wallet:
            raise HTTPException(status_code=404, detail="Associated wallet not found")

        if user.id not in {payer_wallet.user_id, payee_wallet.user_id}:
            raise HTTPException(status_code=403, detail="Not authorized to release this escrow")

        try:
            await update_user_wallet_balance_repo_ext(db=self.db, credentials=payee_wallet.user_id, wallet_type=payee_wallet.wallet_type, amount=escrow.amount_cents)

            execute_transact = TransactionRepository(db=self.db)
            txn_data = TransactionCreate(
                wallet_id=payee_wallet.id,
                users_id=payee_wallet.user_id,
                type=TxnType.deposit,
                amount_cents=escrow.amount_cents,
                status=TxnStatus.completed,
                reference=f"escrow_release_{escrow.id}"
            )
            await execute_transact.create_transaction_ext(txn_data)
            self.notifier.send_escrow_release_credit(payee_user, escrow)

            escrow.status = EscrowStatus.released
            self.db.add(escrow)
            await self.db.commit()

        except Exception as e:
            await self.db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Failed to release escrow due to an error: {str(e)}"
            )

        await self.db.refresh(escrow)
        return await self.repo.get_by_id(escrow_id)


    async def refund_escrow(self, user, escrow_id: uuid.UUID) -> Escrow:
        """
        Refund funds back to payer:
        - only allowed when escrow is 'held'
        - lock rows, credit payer wallet, create transaction, update escrow.status
        """
        qe = Select(Escrow).where(Escrow.id == escrow_id).options(selectinload(Escrow.payer_wallet))
        rese = await self.db.exec(qe)
        escrow = rese.scalars().first()
        if not escrow:
            raise ValueError("Escrow not found")
        if escrow.status != EscrowStatus.held:
            raise ValueError("Only held escrows can be refunded")

        payer_wallet = escrow.payer_wallet

        if str(user.id) != str(payer_wallet.user_id):
            raise PermissionError("Not authorized to refund this escrow")

        await update_user_wallet_balance_repo_ext(
            db=self.db,
            credentials=payer_wallet.user_id,
            wallet_type=payer_wallet.wallet_type,
            amount=escrow.amount_cents
        )

        execute_transact = TransactionRepository(db=self.db)
        txn = TransactionCreate(
            wallet_id=payer_wallet.id,
            users_id=payer_wallet.user_id,
            type=TxnType.refund,
            amount_cents=escrow.amount_cents,
            status=TxnStatus.completed,
            reference=str(escrow.id)
        )
        await execute_transact.create_transaction_ext(txn)
        escrow.status = EscrowStatus.refunded
        self.db.add(escrow)
        await self.db.commit()

        return await self.repo.get_by_id(escrow_id)

    async def dispute_escrow(self, user, escrow_id: uuid.UUID) -> Escrow:
        """
        Mark an escrow as disputed (no funds move).
        Only the payer, payee, or staff/admin should be able to call this.
        """
        qe = Select(Escrow).where(Escrow.id == escrow_id)
        rese = await self.db.exec(qe)
        escrow = rese.scalars().first()
        if not escrow:
            raise ValueError("Escrow not found")
        if escrow.status not in (EscrowStatus.held):
            raise ValueError("Only held escrows can be disputed")

        escrow.status = EscrowStatus.disputed
        self.db.add(escrow)
        await self.db.commit()
        return await self.repo.get_by_id(escrow_id)