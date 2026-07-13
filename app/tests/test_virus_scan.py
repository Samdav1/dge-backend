import pytest
import uuid
import io
from fastapi import UploadFile, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession
from app.db.session import engine
from app.repositories.user_repo import create_user
from app.schemas.user import UserCreate
from app.models.services import Service, ServiceStatus, ServiceType
from app.models.price_negotiation import PriceNegotiation, NegotiationType, NegotiationStatus
from app.models.wallet import Wallet, WalletType
from app.models.escrow import Escrow, EscrowStatus
from app.schemas.work_submission import WorkSubmissionCreate
from app.services.work_submissions import WorkSubmissionService

@pytest.mark.asyncio
async def test_work_submission_virus_and_duplicate_handling():
    async with AsyncSession(engine, expire_on_commit=False) as db:
        # Create client & provider
        client_email = f"client_{uuid.uuid4().hex[:8]}@example.com"
        client = await create_user(db, UserCreate(email=client_email, username=f"client_{uuid.uuid4().hex[:8]}", password="password123", referral_code=None), password="hashed")
        
        provider_email = f"provider_{uuid.uuid4().hex[:8]}@example.com"
        provider = await create_user(db, UserCreate(email=provider_email, username=f"provider_{uuid.uuid4().hex[:8]}", password="password123", referral_code=None), password="hashed")

        # Create wallet & service & negotiation
        client_wallet = Wallet(user_id=client.id, wallet_type=WalletType.deposit, balance_cents=100000, currency="NGN")
        db.add(client_wallet)

        service = Service(
            name="Virus Scan Test Service",
            description="A service to test security",
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

        neg = PriceNegotiation(
            service_id=service.id,
            initiator_id=client.id,
            receiver_id=provider.id,
            negotiation_type=NegotiationType.outgoing,
            proposed_price_cents=50000,
            status=NegotiationStatus.accepted,
            payment_method="platform"
        )
        db.add(neg)
        await db.commit()
        await db.refresh(neg)

        # Create Escrow in held status
        payer_wallet = client_wallet
        provider_wallet = Wallet(user_id=provider.id, wallet_type=WalletType.earnings, balance_cents=0, currency="NGN")
        db.add(provider_wallet)
        await db.commit()
        await db.refresh(provider_wallet)

        escrow = Escrow(
            payer_wallet_id=payer_wallet.id,
            payee_wallet_id=provider_wallet.id,
            payment_negotiation_id=neg.id,
            amount_cents=50000,
            status=EscrowStatus.held,
            payment_method="platform"
        )
        db.add(escrow)
        await db.commit()
        await db.refresh(escrow)

        submission_service = WorkSubmissionService(db)

        # 1. Test scanning & blocking a malicious EICAR file
        eicar_content = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
        malicious_file = UploadFile(
            file=io.BytesIO(eicar_content),
            filename="virus_test.txt",
            headers={"content-type": "text/plain"}
        )
        
        payload = WorkSubmissionCreate(
            escrow_id=escrow.id,
            service_id=service.id,
            text="Here is my work",
            links=[]
        )

        with pytest.raises(HTTPException) as excinfo:
            await submission_service.create_work_submission(
                submission_payload=payload,
                image=None,
                files=malicious_file,
                user=provider
            )
        assert excinfo.value.status_code == 400
        assert "Malware detected" in excinfo.value.detail

        # 2. Test blocking dangerous executable extension (.exe)
        exe_file = UploadFile(
            file=io.BytesIO(b"dummy exe bytes"),
            filename="payload.exe",
            headers={"content-type": "application/x-msdownload"}
        )
        with pytest.raises(HTTPException) as excinfo:
            await submission_service.create_work_submission(
                submission_payload=payload,
                image=None,
                files=exe_file,
                user=provider
            )
        assert excinfo.value.status_code == 400
        assert "Executable file type" in excinfo.value.detail

        # 3. Test submitting a valid ZIP file (should pass)
        zip_file = UploadFile(
            file=io.BytesIO(b"dummy zip content bytes"),
            filename="my_deliverable.zip",
            headers={"content-type": "application/zip"}
        )
        
        sub = await submission_service.create_work_submission(
            submission_payload=payload,
            image=None,
            files=zip_file,
            user=provider
        )
        assert sub is not None
        assert sub.file_urls is not None
        assert len(sub.file_urls) == 1

        # 4. Test submitting duplicate when a submission already exists
        another_zip = UploadFile(
            file=io.BytesIO(b"other zip bytes"),
            filename="my_deliverable2.zip",
            headers={"content-type": "application/zip"}
        )
        with pytest.raises(HTTPException) as excinfo:
            await submission_service.create_work_submission(
                submission_payload=payload,
                image=None,
                files=another_zip,
                user=provider
            )
        assert excinfo.value.status_code == 400
        assert "Work has already been submitted" in excinfo.value.detail

        # Clean up database records
        from app.models.work_submissions import WorkSubmission
        db_sub = await db.get(WorkSubmission, sub.id)
        if db_sub:
            await db.delete(db_sub)
        await db.delete(escrow)
        await db.delete(neg)
        await db.delete(service)
        await db.delete(client_wallet)
        await db.delete(provider_wallet)
        await db.delete(client)
        await db.delete(provider)
        await db.commit()
