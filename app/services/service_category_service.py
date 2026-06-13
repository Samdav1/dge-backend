import uuid
from typing import List, Optional
from sqlmodel import Session
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.services import ServiceCategory, ServiceCategoryLink

from app.schemas.service_category import (
    ServiceCategoryCreate, ServiceCategoryUpdate,
    ServiceCategoryLinkCreate
)
from app.repositories.service_category_repo import (
    ServiceCategoryRepository, ServiceCategoryLinkRepository
)


class ServiceCategoryService:

    def __init__(self, session: AsyncSession):
        self.repo = ServiceCategoryRepository(session)

    async def create_category(self, data: ServiceCategoryCreate) -> ServiceCategory:
        category = ServiceCategory(**data.dict())
        return await self.repo.create_category(category)

    async def get_all_categories(self) -> List[ServiceCategory]:
        return await self.repo.get_all_categories()

    async def get_category(self, category_id: uuid.UUID) -> Optional[ServiceCategory]:
        return await self.repo.get_category_by_id(category_id)

    async def update_category(self, category_id: uuid.UUID, data: ServiceCategoryUpdate) -> Optional[ServiceCategory]:
        category = await self.repo.get_category_by_id(category_id)
        if not category:
            return None
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(category, key, value)
        return await self.repo.update_category(category)

    async def delete_category(self, category_id: uuid.UUID) -> bool:
        category = await self.repo.get_category_by_id(category_id)
        if not category:
            return False
        await self.repo.delete_category(category)
        return True


class ServiceCategoryLinkService:

    def __init__(self, session: AsyncSession):
        self.repo = ServiceCategoryLinkRepository(session)

    async def create_link(self, data: ServiceCategoryLinkCreate) -> ServiceCategoryLink:
        link = ServiceCategoryLink(**data.dict())
        return await self.repo.create_link(link)

    async def get_links_for_service(self, service_id: uuid.UUID) -> List[ServiceCategoryLink]:
        return await self.repo.get_links_by_service(service_id)

    async def delete_link(self, link: ServiceCategoryLink) -> None:
        await self.repo.delete_link(link)
