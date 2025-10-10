# app/services/escrow_service.py
from typing import Optional

from fastapi import HTTPException
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

class EscrowService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = EscrowRepository(db)

    from sqlalchemy.orm import selectinload

    async def create_escrow(self, user, payload: EscrowCreate) -> Escrow:
        """
        Creates an escrow atomically within a single database transaction.
        """
        # Step 1: Eagerly load the negotiation and its related users and wallets.
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

        # Step 2: Perform all validation checks upfront.
        if not negotiation:
            raise HTTPException(status_code=404, detail="Price negotiation not found")

        # --- THIS IS THE COMPLETED LOGIC ---
        # Identify who is the payer and who is the payee.
        initiator = negotiation.initiator
        receiver = negotiation.receiver

        if initiator.id == user.id:
            payer_user = initiator
            payee_user = receiver
        elif receiver.id == user.id:
            payer_user = receiver
            payee_user = initiator
        else:
            # This case should ideally not be hit if the current user is part of the negotiation
            raise HTTPException(status_code=403, detail="Authenticated user is not part of this negotiation.")

        # Extract the first wallet from each user's eagerly loaded list of wallets.
        payer_wallet = payer_user.wallet[1] if payer_user.wallet else None
        payee_wallet = payee_user.wallet[1] if payee_user.wallet else None
        # --- END OF COMPLETED LOGIC ---

        if not payer_wallet or not payee_wallet:
            raise HTTPException(status_code=404, detail="Payer or payee wallet could not be found.")

        # The rest of your validation logic is correct.
        # Note: The check for `payer_wallet.user_id != user.id` is now redundant because we already established it above, but it's kept for safety.
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

        # Step 3: Begin the atomic transaction to modify the database.
        try:
            # Action 1: Deduct funds from the payer's wallet.
            # payer_wallet.balance_cents -= negotiation.proposed_price_cents
            # self.db.add(payer_wallet)
            await update_user_wallet_balance_repo_ext(self.db, wallet_type=payer_wallet.wallet_type, amount=-negotiation.proposed_price_cents, credentials=payer_user.id)

            # Action 2: Create the debit transaction record.
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

            # Action 3: Create the new escrow record.
            new_escrow = Escrow(
                payer_wallet_id=payer_wallet.id,
                payee_wallet_id=payee_wallet.id,
                payment_negotiation_id=negotiation.id,
                amount_cents=negotiation.proposed_price_cents,
                status=EscrowStatus.held
            )
            await self.repo.create_ext(escrow=new_escrow)
            await self.db.commit()

            # Commit all three changes as a single, atomic operation.

        except Exception as e:
            # If any of the above actions fail, roll back everything.
            await self.db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create escrow due to a database error: {str(e)}"
            )

        # Refresh the new escrow object to load its final state from the DB.
        await self.db.refresh(new_escrow)

        return new_escrow

    async def release_escrow(self, user, escrow_id: uuid.UUID) -> Escrow:
        """
        Release escrow funds to the payee within a single atomic transaction.
        """
        # Step 1: Eagerly load the escrow and its related wallets in one async query.
        # This prevents the MissingGreenlet error by avoiding lazy loading.
        query = (
            Select(Escrow)
            .where(Escrow.id == escrow_id)
            .options(
                selectinload(Escrow.payee_wallet),
                selectinload(Escrow.payer_wallet)
            )
        )
        result = await self.db.exec(query)
        escrow = result.scalars().first()

        # Step 2: Perform validation checks.
        if not escrow:
            raise HTTPException(status_code=404, detail="Escrow not found")

        if escrow.status != EscrowStatus.held:
            raise HTTPException(status_code=400, detail="Only held escrows can be released")

        # Use the eagerly loaded relationships.
        payee_wallet = escrow.payee_wallet
        payer_wallet = escrow.payer_wallet

        if not payee_wallet or not payer_wallet:
            raise HTTPException(status_code=404, detail="Associated wallet not found")

        # Step 3: Check authorization.
        if user.id not in {payer_wallet.user_id, payee_wallet.user_id}:
            raise HTTPException(status_code=403, detail="Not authorized to release this escrow")

        # Step 4: Perform all database modifications within a single transaction.
        try:
            # Credit the payee's wallet.
            await update_user_wallet_balance_repo_ext(db=self.db, credentials=payee_wallet.user_id, wallet_type=payee_wallet.wallet_type, amount=escrow.amount_cents)

            # Create a transaction record for the credit.
            execute_transact = TransactionRepository(db=self.db)
            txn_data = TransactionCreate(
                wallet_id=payee_wallet.id,  # The credit goes to the payee's wallet
                users_id=payee_wallet.user_id,
                type=TxnType.deposit,  # This is a deposit for the payee
                amount_cents=escrow.amount_cents,
                status=TxnStatus.completed,
                reference=f"escrow_release_{escrow.id}"
            )
            await execute_transact.create_transaction_ext(txn_data)

            # Update the escrow status to released.
            escrow.status = EscrowStatus.released
            self.db.add(escrow)

            # Commit all changes at once.
            await self.db.commit()

        except Exception as e:
            # If any step fails, roll back the entire transaction.
            await self.db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Failed to release escrow due to an error: {str(e)}"
            )

        # Refresh the object to get the updated state from the database.
        await self.db.refresh(escrow)

        return escrow

    # return updated escrow
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

        # only authorized users (payer or admin) can trigger refund
        if str(user.id) != str(payer_wallet.user_id):
            raise PermissionError("Not authorized to refund this escrow")

        # credit payer back
        # payer_wallet.balance_cents += escrow.amount_cents
        # self.db.add(payer_wallet)
        await update_user_wallet_balance_repo_ext(
            db=self.db,
            credentials=payer_wallet.user_id,
            wallet_type=payer_wallet.wallet_type,
            amount=escrow.amount_cents
        )

        # create refund transaction
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

        # save status = disputed
        escrow.status = EscrowStatus.disputed
        self.db.add(escrow)
        await self.db.commit()
        return await self.repo.get_by_id(escrow_id)