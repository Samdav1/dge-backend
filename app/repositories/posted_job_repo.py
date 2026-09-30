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

    async def list_open(
        self,
        category_id: Optional[uuid.UUID] = None,
        search: Optional[str] = None,
        country: Optional[str] = None,
        state: Optional[str] = None,
        city: Optional[str] = None,
        near_me: Optional[bool] = False,
        user_profile: Optional[object] = None,
    ) -> List[PostedJob]:
        from app.models.user import Users
        from app.models.profile import Profile
        from sqlalchemy import or_

        query = (
            select(PostedJob)
            .where(PostedJob.status == PostedJobStatus.open)
            .outerjoin(PostedJob.user)
            .outerjoin(Users.profile)
            .options(
                selectinload(PostedJob.user),
                selectinload(PostedJob.category),
            )
        )
        if category_id:
            query = query.where(PostedJob.category_id == category_id)
        if search:
            search_pat = f"%{search}%"
            query = query.where(or_(
                PostedJob.title.ilike(search_pat),
                PostedJob.description.ilike(search_pat)
            ))

        if near_me and user_profile:
            loc_conds = []
            user_city = getattr(user_profile, "city", None)
            user_state = getattr(user_profile, "state", None)
            if user_city:
                c_pat = f"%{user_city.strip()}%"
                loc_conds.append(PostedJob.description.ilike(c_pat))
                loc_conds.append(Profile.city.ilike(c_pat))
            if user_state:
                s_pat = f"%{user_state.strip()}%"
                loc_conds.append(PostedJob.description.ilike(s_pat))
                loc_conds.append(Profile.state.ilike(s_pat))
            if loc_conds:
                query = query.where(or_(*loc_conds))
        else:
            if city and city.strip():
                city_pat = f"%{city.strip()}%"
                query = query.where(or_(
                    PostedJob.description.ilike(city_pat),
                    Profile.city.ilike(city_pat)
                ))
            if state and state.strip():
                state_pat = f"%{state.strip()}%"
                query = query.where(or_(
                    PostedJob.description.ilike(state_pat),
                    Profile.state.ilike(state_pat)
                ))
            if country and country.strip():
                country_pat = f"%{country.strip()}%"
                query = query.where(or_(
                    PostedJob.description.ilike(country_pat),
                    Profile.country.ilike(country_pat)
                ))

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
            try:
                from app.services import points_service
                await points_service.record_failed_negotiation(
                    db=self.db,
                    user_id=bid.initiator_id,
                    context="posted_job"
                )
            except Exception as e:
                print(f"[Points] Error recording unaccepted bid for provider {bid.initiator_id}: {e}")
        await self.db.commit()
