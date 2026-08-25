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
from app.schemas.escrow import EscrowActionPayload
from app.schemas.conversation import ConversationCreate, ConversationType
from app.repositories.conversation_repo import insert_conversation_into_db
from app.schemas.messages import MessageCreate, MessageContentType
from app.repositories.messages_repo import MessageRepository
from app.services.messages_service import MessageService
from app.schemas.portfolio import UserPortfolioCreate
from app.repositories.portfolio_repo import get_portfolio_repo, create_portfolio_repo
from app.schemas.reviews import ReviewCreate
from app.services.reviews_service import ReviewService
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
                selectinload(PriceNegotiation.services),
            )
        )
        result = await self.db.exec(query)
        negotiation = result.scalars().first()

        if not negotiation:
            raise HTTPException(status_code=404, detail="Price negotiation not found")


        initiator = negotiation.initiator
        receiver = negotiation.receiver

        if user.id not in (initiator.id, receiver.id):
            raise HTTPException(status_code=403, detail="Authenticated user is not part of this negotiation.")

        service = negotiation.services
        if not service:
            raise HTTPException(status_code=400, detail="Service not found for this negotiation")

        if initiator.id == service.user_id:
            payee_user = initiator
            payer_user = receiver
        elif receiver.id == service.user_id:
            payee_user = receiver
            payer_user = initiator
        else:
            raise HTTPException(status_code=400, detail="Cannot determine service provider for this negotiation")

        from app.models.wallet import WalletType
        payer_wallet = next((w for w in payer_user.wallet if w.wallet_type == WalletType.deposit), None) if payer_user.wallet else None
        if not payer_wallet:
            payer_wallet = Wallet(user_id=payer_user.id, wallet_type=WalletType.deposit, balance_cents=0, currency="NGN")
            self.db.add(payer_wallet)
            await self.db.flush()
            if payer_user.wallet is None:
                payer_user.wallet = []
            payer_user.wallet.append(payer_wallet)

        payee_wallet = next((w for w in payee_user.wallet if w.wallet_type == WalletType.earnings), None) if payee_user.wallet else None
        if not payee_wallet:
            payee_wallet = Wallet(user_id=payee_user.id, wallet_type=WalletType.earnings, balance_cents=0, currency="NGN")
            self.db.add(payee_wallet)
            await self.db.flush()
            if payee_user.wallet is None:
                payee_user.wallet = []
            payee_user.wallet.append(payee_wallet)


        if payer_wallet.user_id != payer_user.id:
            raise HTTPException(status_code=403, detail="Payer wallet is not owned by the client")

        if negotiation.proposed_price_cents != payload.amount_cents:
            raise HTTPException(status_code=400, detail="Payload amount does not match the negotiated amount")

        if payload.payment_method != "cash":
            if payer_wallet.balance_cents < negotiation.proposed_price_cents:
                print('testing', payer_wallet)
                raise HTTPException(status_code=402, detail="Insufficient funds in payer wallet")

        existing_escrow = await self.repo.get_by_negotiation(payload.payment_negotiation_id)
        if existing_escrow:
            raise HTTPException(status_code=409, detail="An escrow already exists for this negotiation")

        try:
            if payload.payment_method != "cash":
                await update_user_wallet_balance_repo_ext(self.db, wallet_type=payer_wallet.wallet_type, amount=-negotiation.proposed_price_cents, credentials=payer_user.id)

                execute_transact = TransactionRepository(db=self.db)
                txn_data = TransactionCreate(
                    wallet_id=payer_wallet.id,
                    users_id=payer_user.id,
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
                status=EscrowStatus.held,
                payment_method=payload.payment_method or "platform"
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

    async def release_escrow(self, user, escrow_id: uuid.UUID, payload: Optional[EscrowActionPayload] = None) -> Escrow:
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

        if escrow.status not in (EscrowStatus.held, EscrowStatus.disputed):
            raise HTTPException(status_code=400, detail="Only held or disputed escrows can be released")

        payee_wallet = escrow.payee_wallet
        payer_wallet = escrow.payer_wallet
        payee_user = payee_wallet.user
        payer_user = payer_wallet.user

        if not payee_wallet or not payer_wallet:
            raise HTTPException(status_code=404, detail="Associated wallet not found")

        if user.id not in {payer_wallet.user_id, payee_wallet.user_id}:
            raise HTTPException(status_code=403, detail="Not authorized to release this escrow")

        was_disputed = (escrow.status == EscrowStatus.disputed)

        try:
            if escrow.payment_method != "cash":
                from app.services.fee_service import fee_service
                fee_cents, net_cents = await fee_service.apply_fee(
                    db=self.db,
                    event_type="escrow_release",
                    user_id=payee_wallet.user_id,
                    gross_amount_cents=escrow.amount_cents,
                    reference=str(escrow.id)
                )

                await update_user_wallet_balance_repo_ext(db=self.db, credentials=payee_wallet.user_id, wallet_type=payee_wallet.wallet_type, amount=net_cents)

                execute_transact = TransactionRepository(db=self.db)
                txn_data = TransactionCreate(
                    wallet_id=payee_wallet.id,
                    users_id=payee_wallet.user_id,
                    type=TxnType.deposit,
                    amount_cents=net_cents,
                    status=TxnStatus.completed,
                    reference=f"escrow_release_{escrow.id}"
                )
                await execute_transact.create_transaction_ext(txn_data)
                self.notifier.send_escrow_release_credit(
                    payee=payee_user,
                    escrow=escrow,
                    payer=payer_user,
                    is_dispute_resolution=was_disputed
                )

            escrow.status = EscrowStatus.released
            self.db.add(escrow)
            await self.db.commit()

        except Exception as e:
            await self.db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Failed to release escrow due to an error: {str(e)}"
            )

        # Handle review and direct message from payload
        if payload:
            # Send Direct Message
            if payload.direct_message:
                try:
                    conv_create = ConversationCreate(type=ConversationType.private, recipient_id=payee_user.id)
                    conversation = await insert_conversation_into_db(self.db, conv_create, user.id)
                    
                    msg_create = MessageCreate(
                        content=payload.direct_message,
                        content_type=MessageContentType.text,
                        conversation_id=conversation.id,
                        sender_id=user.id
                    )
                    msg_repo = MessageRepository(self.db)
                    msg_svc = MessageService(msg_repo)
                    await msg_svc.create_message(msg_create)
                except Exception as e:
                    print(f"Failed to create direct message: {e}")

            # Create Review
            if payload.rating is not None and payload.review_comment:
                try:
                    try:
                        portfolio = await get_portfolio_repo(self.db, payee_user.id)
                    except HTTPException as he:
                        if he.status_code == 404:
                            p_info = UserPortfolioCreate(title=f"{payee_user.username}'s Portfolio", description="Auto-generated portfolio", category="General")
                            portfolio = await create_portfolio_repo(p_info, self.db, payee_user.id)
                        else:
                            raise he

                    rev_create = ReviewCreate(
                        rating=payload.rating,
                        comment=payload.review_comment,
                        portfolio_id=portfolio.id,
                        user_id=user.id
                    )
                    await ReviewService.create_review(self.db, rev_create)
                except Exception as e:
                    print(f"Failed to create review: {e}")

        await self.db.refresh(escrow)
        return await self.repo.get_by_id(escrow_id)


    async def refund_escrow(self, user, escrow_id: uuid.UUID) -> Escrow:
        """
        Refund funds back to payer:
        - allowed when escrow is 'held' or 'disputed'
        - lock rows, credit payer wallet, create transaction, update escrow.status
        """
        qe = Select(Escrow).where(Escrow.id == escrow_id).options(
            selectinload(Escrow.payer_wallet).options(selectinload(Wallet.user)),
            selectinload(Escrow.payee_wallet).options(selectinload(Wallet.user))
        )
        rese = await self.db.exec(qe)
        escrow = rese.scalars().first()
        if not escrow:
            raise ValueError("Escrow not found")
        if escrow.status not in (EscrowStatus.held, EscrowStatus.disputed):
            raise ValueError("Only held or disputed escrows can be refunded")

        was_disputed = (escrow.status == EscrowStatus.disputed)
        payer_wallet = escrow.payer_wallet
        payee_wallet = escrow.payee_wallet
        payer = payer_wallet.user if payer_wallet else None
        payee = payee_wallet.user if payee_wallet else None

        if str(user.id) != str(payer_wallet.user_id):
            # Allow admin refund bypass
            pass

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
        await self.db.refresh(escrow)
        self.notifier.send_escrow_refund_mail(
            payer=payer,
            escrow=escrow,
            payee=payee,
            is_dispute_resolution=was_disputed
        )
        return escrow

    async def dispute_escrow(self, user, escrow_id: uuid.UUID, payload: Optional[EscrowActionPayload] = None) -> Escrow:
        """
        Mark an escrow as disputed (no funds move).
        Only the payer, payee, or staff/admin should be able to call this.
        """
        qe = Select(Escrow).where(Escrow.id == escrow_id).options(
            selectinload(Escrow.payer_wallet).options(selectinload(Wallet.user)),
            selectinload(Escrow.payee_wallet).options(selectinload(Wallet.user))
        )
        rese = await self.db.exec(qe)
        escrow = rese.scalars().first()
        if not escrow:
            raise ValueError("Escrow not found")
        if escrow.status not in (EscrowStatus.held, EscrowStatus.released):
            raise ValueError("Only held or completed (released) escrows can be disputed")

        escrow.status = EscrowStatus.disputed
        payer = escrow.payer_wallet.user
        payee = escrow.payee_wallet.user
        self.db.add(escrow)
        await self.db.commit()
        await self.db.refresh(escrow)

        if payload and payload.direct_message:
            try:
                # Determine recipient (the other party)
                recipient_id = payee.id if user.id == payer.id else payer.id
                conv_create = ConversationCreate(type=ConversationType.private, recipient_id=recipient_id)
                conversation = await insert_conversation_into_db(self.db, conv_create, user.id)
                
                msg_create = MessageCreate(
                    content=payload.direct_message,
                    content_type=MessageContentType.text,
                    conversation_id=conversation.id,
                    sender_id=user.id
                )
                msg_repo = MessageRepository(self.db)
                msg_svc = MessageService(msg_repo)
                await msg_svc.create_message(msg_create)
            except Exception as e:
                print(f"Failed to create direct message for dispute: {e}")

        self.notifier.send_escrow_dispute_mail(payer=payer, payee=payee, escrow=escrow)
        return escrow
