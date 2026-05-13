# app/repositories/service_repository.py
import uuid
from typing import List, Optional

from sqlmodel import select, or_
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from app.models import Users
from app.models.services import Service, ServiceCategoryLink
from app.schemas.user import UserRead


class ServiceRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, service: Service, category_ids: Optional[List[uuid.UUID]] = None) -> Service:
        self.session.add(service)
        await self.session.commit()
        await self.session.refresh(service)

        if category_ids:
            for cid in category_ids:
                link = ServiceCategoryLink(service_id=service.id, category_id=cid)
                self.session.add(link)
            await self.session.commit()

        # re-fetch with categories eager-loaded
        q = select(Service).where(Service.id == service.id).options(selectinload(Service.categories))
        result = await self.session.exec(q)
        return result.first()

    async def list(
            self,
            *,
            user_id: Optional[uuid.UUID] = None,
            status=None,
            type=None,
            search: Optional[str] = None,
            category_id: Optional[uuid.UUID] = None,
            offset: int = 0,  # Added for performance
            limit: int = 100,  # Added to prevent memory crashes
    ) -> List[Service]:

        q = select(Service).options(
            selectinload(Service.categories),
            joinedload(Service.user).options(
                joinedload(Users.profile),
                selectinload(Users.portfolios)
            )
        )

        if user_id:
            q = q.where(Service.user_id == user_id)
        if status:
            q = q.where(Service.status == status)
        if type:
            q = q.where(Service.type == type)
        if search:
            search_pattern = f"%{search}%"
            q = q.where(or_(Service.name.ilike(search_pattern), Service.description.ilike(search_pattern)))
        if category_id:
            q = q.join(ServiceCategoryLink).where(ServiceCategoryLink.category_id == category_id)

        q = q.offset(offset).limit(limit)

        result = await self.session.exec(q)
        return result.all()

    async def get(self, service_id: uuid.UUID):
        q = select(Service).where(Service.id == service_id).options(
            selectinload(Service.categories),
            selectinload(Service.user).options(selectinload(Users.profile), selectinload(Users.portfolios)))

        result = await self.session.exec(q)
        service = result.first()
        profile = service.user.profile
        portfolio = service.user.portfolios
        user = UserRead.model_validate(service.user)
        return {"service": service, "profile": profile, "portfolio": portfolio, "user": user}

    async def update(self, service: Service, category_ids: Optional[List[uuid.UUID]] = None) -> Service:
        self.session.add(service)
        await self.session.commit()
        await self.session.refresh(service)

        if category_ids is not None:
            # delete old links
            q = select(ServiceCategoryLink).where(ServiceCategoryLink.service_id == service.id)
            links = await self.session.exec(q).scalars().all()
            for link in links:
                await self.session.delete(link)
            await self.session.commit()

            # add new links
            for cid in category_ids:
                self.session.add(ServiceCategoryLink(service_id=service.id, category_id=cid))
            await self.session.commit()

        # return re-fetched service with categories
        q2 = select(Service).where(Service.id == service.id).options(selectinload(Service.categories))
        result = await self.session.exec(q2)
        return result.first()

    async def delete(self, service: Service) -> None:
        await self.session.delete(service)
        await self.session.commit()