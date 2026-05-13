import uuid
from typing import List, Optional

from fastapi import HTTPException
from sqlmodel import select, func
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.posted_job import PostedJob, PostedJobStatus
from app.models.price_negotiation import PriceNegotiation
from app.models.services import ServiceCategory
from app.schemas.posted_job import PostedJobCreate, PostedJobRead


class PostedJobRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, job: PostedJob) -> PostedJob:
        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)
        return job

    async def get_by_id(self, job_id: uuid.UUID) -> Optional[PostedJob]:
        result = await self.db.execute(
            select(PostedJob)
            .where(PostedJob.id == job_id)
            .options(
                selectinload(PostedJob.user),
                selectinload(PostedJob.category),
            )
        )
        return result.scalar_one_or_none()

    async def list_open(self, category_id: Optional[uuid.UUID] = None, search: Optional[str] = None) -> List[PostedJob]:
        query = select(PostedJob).where(PostedJob.status == PostedJobStatus.open).options(
            selectinload(PostedJob.user),
            selectinload(PostedJob.category),
        )
        if category_id:
            query = query.where(PostedJob.category_id == category_id)
        if search:
            query = query.where(PostedJob.title.ilike(f"%{search}%"))
        result = await self.db.execute(query.order_by(PostedJob.created_at.desc()))
        return result.scalars().all()

    async def list_for_user(self, user_id: uuid.UUID) -> List[PostedJob]:
        result = await self.db.execute(
            select(PostedJob)
            .where(PostedJob.user_id == user_id)
            .options(
                selectinload(PostedJob.user),
                selectinload(PostedJob.category),
            )
            .order_by(PostedJob.created_at.desc())
        )
        return result.scalars().all()

    async def get_bid_count(self, job_id: uuid.UUID) -> int:
        result = await self.db.execute(
            select(func.count(PriceNegotiation.id)).where(PriceNegotiation.posted_job_id == job_id)
        )
        return result.scalar_one() or 0

    async def update(self, job: PostedJob, updates: dict) -> PostedJob:
        for key, value in updates.items():
            setattr(job, key, value)
        await self.db.commit()
        await self.db.refresh(job)
        return job

    async def get_job_bids(self, job_id: uuid.UUID) -> List[PriceNegotiation]:
        from app.models.services import Service
        from sqlalchemy.orm import selectinload as sl
        result = await self.db.execute(
            select(PriceNegotiation)
            .where(PriceNegotiation.posted_job_id == job_id)
            .options(
                sl(PriceNegotiation.services).selectinload(Service.categories),
                sl(PriceNegotiation.initiator),
                sl(PriceNegotiation.receiver),
            )
        )
        return result.scalars().all()

    async def reject_other_bids(self, job_id: uuid.UUID, accepted_bid_id: uuid.UUID):
        from app.models.price_negotiation import NegotiationStatus
        result = await self.db.execute(
            select(PriceNegotiation).where(
                PriceNegotiation.posted_job_id == job_id,
                PriceNegotiation.id != accepted_bid_id,
                PriceNegotiation.status == NegotiationStatus.pending
            )
        )
        bids = result.scalars().all()
        for bid in bids:
            bid.status = NegotiationStatus.rejected
            self.db.add(bid)
        await self.db.commit()
