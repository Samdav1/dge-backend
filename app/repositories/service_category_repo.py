from sqlmodel import Session, select
from typing import List, Optional

from sqlmodel.ext.asyncio.session import AsyncSession
from app.models.services import ServiceCategory, ServiceCategoryLink
from app.schemas.service_category import ServiceCategoryCreate, ServiceCategoryUpdate


class ServiceCategoryRepository:

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_category(self, category: ServiceCategory) -> ServiceCategory:
        self.session.add(category)
        await self.session.commit()
        await self.session.refresh(category)
        return category

    async def get_category_by_id(self, category_id) -> Optional[ServiceCategory]:
        return await self.session.get(ServiceCategory, category_id)

    async def get_all_categories(self) -> List[ServiceCategory]:
        result = await self.session.exec(select(ServiceCategory))
        refined = result.all()
        return refined

    async def update_category(self, category: ServiceCategory) -> ServiceCategory:
        self.session.add(category)
        await self.session.commit()
        await self.session.refresh(category)
        return category

    async def delete_category(self, category: ServiceCategory) -> None:
        await self.session.delete(category)
        await self.session.commit()


class ServiceCategoryLinkRepository:

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_link(self, link: ServiceCategoryLink) -> ServiceCategoryLink:
        self.session.add(link)
        await self.session.commit()
        await self.session.refresh(link)
        return link

    async def get_links_by_service(self, service_id) -> List[ServiceCategoryLink]:
        stmt = select(ServiceCategoryLink).where(ServiceCategoryLink.service_id == service_id)
        result = await self.session.exec(stmt)
        return result.all()

    async def delete_link(self, link: ServiceCategoryLink) -> None:
        await self.session.delete(link)
        await self.session.commit()