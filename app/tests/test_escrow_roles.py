import pytest
import uuid
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from app.db.session import engine
from app.repositories.user_repo import create_user
from app.schemas.user import UserCreate
from app.models import Users
from app.models.services import Service, ServiceStatus, ServiceType
from app.models.price_negotiation import PriceNegotiation, NegotiationType, NegotiationStatus
from app.models.wallet import Wallet, WalletType
from app.schemas.escrow import EscrowCreate
from app.services.escrow_service import EscrowService

@pytest.mark.asyncio
async def test_escrow_role_resolution():
    async with AsyncSession(engine, expire_on_commit=False) as db:
        # Create client user
        client_email = f"client_{uuid.uuid4().hex[:8]}@example.com"
        client = await create_user(db, UserCreate(email=client_email, username=f"client_{uuid.uuid4().hex[:8]}", password="password123", referral_code=None), password="hashed")
        
        # Create provider user
        provider_email = f"provider_{uuid.uuid4().hex[:8]}@example.com"
        provider = await create_user(db, UserCreate(email=provider_email, username=f"provider_{uuid.uuid4().hex[:8]}", password="password123", referral_code=None), password="hashed")

        # Give client deposit wallet balance
        client_wallet = Wallet(user_id=client.id, wallet_type=WalletType.deposit, balance_cents=100000, currency="NGN")
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
        await db.refresh(client)
        await db.refresh(provider)
        await db.refresh(service)

        # Create price negotiation initiated by client
        neg = PriceNegotiation(
            service_id=service.id,
            initiator_id=client.id,
            receiver_id=provider.id,
            negotiation_type=NegotiationType.outgoing,
            proposed_price_cents=50000, # ₦500
            status=NegotiationStatus.pending,
            payment_method="platform"
        )
        db.add(neg)
        await db.commit()
        await db.refresh(neg)

        # Provider accepts -> Escrow is created. 
        # Inside the service, user is the provider (receiver) who accepted the offer.
        escrow_service = EscrowService(db)
        payload = EscrowCreate(
            payment_negotiation_id=neg.id,
            amount_cents=50000,
            reference=f"test_ref_{uuid.uuid4().hex}",
            payment_method="platform"
        )
        
        # Provider (user=provider) accepting should correctly debit client wallet and credit payee to provider
        escrow = await escrow_service.create_escrow(user=provider, payload=payload)
        
        assert escrow.payer_wallet_id == client_wallet.id
        # Reload client wallet to verify balance deduction
        await db.refresh(client_wallet)
        assert client_wallet.balance_cents == 50000 # 100000 - 50000

        # Clean up
        await db.delete(escrow)
        await db.delete(neg)
        await db.delete(service)
        
        from app.models.transactions import Transaction
        txns_res = await db.execute(select(Transaction).where(Transaction.wallet_id == client_wallet.id))
        for tx in txns_res.scalars().all():
            await db.delete(tx)

        await db.delete(client_wallet)
        # Check if provider has earnings wallet created
        p_earning_wallet_res = await db.execute(select(Wallet).where(Wallet.user_id == provider.id, Wallet.wallet_type == WalletType.earnings))
        p_earning_wallet = p_earning_wallet_res.scalars().first()
        if p_earning_wallet:
            await db.delete(p_earning_wallet)
        await db.delete(client)
        await db.delete(provider)
        await db.commit()
