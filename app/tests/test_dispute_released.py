import pytest
import uuid
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from app.db.session import engine
from app.repositories.user_repo import create_user
from app.schemas.user import UserCreate
from app.models.services import Service, ServiceStatus, ServiceType
from app.models.price_negotiation import PriceNegotiation, NegotiationType, NegotiationStatus
from app.models.wallet import Wallet, WalletType
from app.schemas.escrow import EscrowCreate, EscrowActionPayload
from app.services.escrow_service import EscrowService

@pytest.mark.asyncio
async def test_dispute_released_escrow():
    async with AsyncSession(engine, expire_on_commit=False) as db:
        # Create client user
        client_email = f"client_{uuid.uuid4().hex[:8]}@example.com"
        client = await create_user(db, UserCreate(email=client_email, username=f"client_{uuid.uuid4().hex[:8]}", password="password123", referral_code=None), password="hashed")
        
        # Create provider user
        provider_email = f"provider_{uuid.uuid4().hex[:8]}@example.com"
        provider = await create_user(db, UserCreate(email=provider_email, username=f"provider_{uuid.uuid4().hex[:8]}", password="password123", referral_code=None), password="hashed")

        # Give client deposit wallet balance
        client_wallet = Wallet(user_id=client.id, wallet_type=WalletType.deposit, balance_cents=10000000, currency="NGN")
        db.add(client_wallet)
        
        # Create service owned by provider
        service = Service(
            name="Test Dev Service",
            description="Test Dev Desc",
            type=ServiceType.online,
            username=provider.username,
            user_id=provider.id,
            status=ServiceStatus.approved,
            price=1000.00
        )
        db.add(service)
        await db.commit()

        # Create price negotiation initiated by client
        neg = PriceNegotiation(
            service_id=service.id,
            initiator_id=client.id,
            receiver_id=provider.id,
            negotiation_type=NegotiationType.outgoing,
            proposed_price_cents=5000000, # ₦50000
            status=NegotiationStatus.pending,
            payment_method="platform"
        )
        db.add(neg)
        await db.commit()

        escrow_service = EscrowService(db)
        payload = EscrowCreate(
            payment_negotiation_id=neg.id,
            amount_cents=5000000,
            reference=f"test_ref_{uuid.uuid4().hex}",
            payment_method="platform"
        )
        
        # Provider accepts -> Escrow is held
        escrow = await escrow_service.create_escrow(user=provider, payload=payload)
        assert escrow.status == "held"

        # Client releases escrow (completed/released)
        # We need to refresh provider since create_escrow might have touched the database/earnings wallet creation
        await db.refresh(provider)
        escrow = await escrow_service.release_escrow(user=client, escrow_id=escrow.id)
        assert escrow.status == "released"

        # Now, client disputes the completed (released) escrow
        escrow = await escrow_service.dispute_escrow(user=client, escrow_id=escrow.id, payload=EscrowActionPayload(direct_message="Disputing completed escrow due to issue"))
        assert escrow.status == "disputed"

        # Clean up
        await db.delete(escrow)
        await db.delete(neg)
        await db.delete(service)
        
        from app.models.transactions import Transaction
        from app.models.messages import Message
        from app.models.conversation import Conversation, ConversationParticipant

        # Delete message read receipts
        from app.models.messages import MessageReadReceipt
        receipts_res = await db.execute(select(MessageReadReceipt))
        for r in receipts_res.scalars().all():
            await db.delete(r)

        # Delete messages
        msgs_res = await db.execute(select(Message))
        for msg in msgs_res.scalars().all():
            await db.delete(msg)

        # Delete conversation participants
        parts_res = await db.execute(select(ConversationParticipant))
        for part in parts_res.scalars().all():
            await db.delete(part)

        # Delete conversations
        convs_res = await db.execute(select(Conversation))
        for conv in convs_res.scalars().all():
            await db.delete(conv)
        
        # Delete all transactions
        txns_res = await db.execute(select(Transaction))
        for tx in txns_res.scalars().all():
            await db.delete(tx)

        # Delete all platform revenue logs
        from app.models.admin import PlatformRevenueLog
        logs_res = await db.execute(select(PlatformRevenueLog))
        for log in logs_res.scalars().all():
            await db.delete(log)

        # Delete wallets
        await db.delete(client_wallet)
        p_earning_wallet_res = await db.execute(select(Wallet).where(Wallet.user_id == provider.id, Wallet.wallet_type == WalletType.earnings))
        p_earning_wallet = p_earning_wallet_res.scalars().first()
        if p_earning_wallet:
            await db.delete(p_earning_wallet)
            
        await db.delete(client)
        await db.delete(provider)
        await db.commit()
