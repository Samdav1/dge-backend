import uuid
from typing import List, Optional

from fastapi import HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.posted_job import PostedJob, PostedJobStatus
from app.models.wallet import Wallet, WalletType
from app.repositories.posted_job_repo import PostedJobRepository
from app.schemas.posted_job import PostedJobCreate, PostedJobRead, PostedJobUpdate
from app.schemas.price_negotiation import PriceNegotiationRead


class PostedJobService:
    def __init__(self, repo: PostedJobRepository, db: AsyncSession):
        self.repo = repo
        self.db = db

    async def _get_user_wallet(self, user_id: uuid.UUID) -> Optional[Wallet]:
        result = await self.db.execute(
            select(Wallet).where(
                Wallet.user_id == user_id,
                Wallet.wallet_type == WalletType.deposit
            )
        )
        return result.scalar_one_or_none()

    async def create_posted_job(self, payload: PostedJobCreate, user_id: uuid.UUID) -> PostedJobRead:
        # Check wallet balance covers max_price ONLY if payment method is platform
        if payload.payment_method != "cash":
            wallet = await self._get_user_wallet(user_id)
            if not wallet:
                raise HTTPException(status_code=400, detail="No deposit wallet found. Please fund your wallet first.")
            if wallet.balance_cents < payload.max_price_cents:
                raise HTTPException(
                    status_code=400,
                    detail=f"Insufficient wallet balance. You need at least ${payload.max_price_cents / 100:.2f} to post this job."
                )

        job = PostedJob(
            user_id=user_id,
            title=payload.title,
            description=payload.description,
            category_id=payload.category_id,
            min_price_cents=payload.min_price_cents,
            max_price_cents=payload.max_price_cents,
            image=payload.image,
            payment_method=payload.payment_method or "platform",
            status=PostedJobStatus.open,
        )
        created = await self.repo.create(job)
        # Reload with relationships
        full = await self.repo.get_by_id(created.id)

        try:
            from app.repositories.user_repo import get_user_by_id
            user = await get_user_by_id(user_id, self.db)
            if user:
                from app.services.email_notification_service import NotificationService
                NotificationService().send_job_posted_mail(user, full)
        except Exception as e:
            print(f"Failed to send job_posted email: {e}")

        return PostedJobRead.model_validate(full)

    async def list_open_jobs(
        self,
        category_id: Optional[uuid.UUID] = None,
        search: Optional[str] = None,
        country: Optional[str] = None,
        state: Optional[str] = None,
        city: Optional[str] = None,
        near_me: Optional[bool] = False,
        user_profile: Optional[object] = None,
    ) -> List[PostedJobRead]:
        jobs = await self.repo.list_open(
            category_id=category_id,
            search=search,
            country=country,
            state=state,
            city=city,
            near_me=near_me,
            user_profile=user_profile,
        )
        result = []
        for j in jobs:
            schema = PostedJobRead.model_validate(j)
            schema.bid_count = await self.repo.get_bid_count(j.id)
            result.append(schema)
        return result

    async def list_my_jobs(self, user_id: uuid.UUID) -> List[PostedJobRead]:
        jobs = await self.repo.list_for_user(user_id)
        result = []
        for j in jobs:
            schema = PostedJobRead.model_validate(j)
            schema.bid_count = await self.repo.get_bid_count(j.id)
            result.append(schema)
        return result

    async def get_job(self, job_id: uuid.UUID) -> PostedJobRead:
        job = await self.repo.get_by_id(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Posted job not found")
        schema = PostedJobRead.model_validate(job)
        schema.bid_count = await self.repo.get_bid_count(job_id)
        return schema

    async def get_job_bids(self, job_id: uuid.UUID, user_id: uuid.UUID) -> List[PriceNegotiationRead]:
        job = await self.repo.get_by_id(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Posted job not found")
        if job.user_id != user_id:
            raise HTTPException(status_code=403, detail="You can only view bids on your own jobs")

        bids = await self.repo.get_job_bids(job_id)
        from app.schemas.price_negotiation import PriceNegotiationRead
        return [PriceNegotiationRead.model_validate(b) for b in bids]

    async def cancel_job(self, job_id: uuid.UUID, user_id: uuid.UUID) -> PostedJobRead:
        job = await self.repo.get_by_id(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Posted job not found")
        if job.user_id != user_id:
            raise HTTPException(status_code=403, detail="You can only cancel your own jobs")
        if job.status != PostedJobStatus.open:
            raise HTTPException(status_code=400, detail="Only open jobs can be cancelled")
        updated = await self.repo.update(job, {"status": PostedJobStatus.cancelled})
        return PostedJobRead.model_validate(updated)
