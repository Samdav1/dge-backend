# app/services/service_service.py
import os
import uuid
import json
from typing import Optional, List
from fastapi import UploadFile, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.services_repo import ServiceRepository
from app.schemas.services import ServiceCreate, ServiceUpdate
from app.models.services import Service, ServiceStatus
from app.dependencies.file_handler import save_service_image, save_avatar
from app.schemas.user import UserRead


ALLOWED_IMAGE_MIMES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


class ServiceService:
    def __init__(self, repo: ServiceRepository):
        self.repo = repo

    async def create_service(
            self,
            db: AsyncSession,
            user: UserRead,
            payload: ServiceCreate,
            image: Optional[UploadFile] = None,
    ) -> Service:
        image_path = None
        if image:
            if image.content_type not in ALLOWED_IMAGE_MIMES:
                raise HTTPException(status_code=400, detail="Unsupported image type")
            image_path = await save_service_image(image)

        service = Service(
            name=payload.name,
            description=payload.description,
            price=payload.price,
            discount=payload.discount,
            discount_percent=payload.discount_percent,
            type=payload.type,
            user_id=user.id,
            username=user.username,
            meta_tags=payload.meta_tags,
            keywords=payload.keywords,
            image=image_path,
            status=ServiceStatus.pending_review,
        )
        return await self.repo.create(service, payload.category_ids)

    async def list_services(self, *, user_id=None, status=None, type=None, search=None, category_id=None, offset: int = 0, limit: int = 100, sort_by: str = "newest") -> List[Service]:
        return await self.repo.list(user_id=user_id, status=status, type=type, search=search, category_id=category_id, offset=offset, limit=limit, sort_by=sort_by)

    async def get_service(self, service_id: uuid.UUID):
        service = await self.repo.get(service_id)
        if not service:
            raise HTTPException(status_code=404, detail="Service not found")
        return service

    async def update_service(
            self,
            db: AsyncSession,
            service_id: uuid.UUID,
            user: UserRead,
            payload: ServiceUpdate,
            image: Optional[UploadFile] = None,
    ) -> Service:
        result = await self.repo.get(service_id)
        if not result:
            raise HTTPException(status_code=404, detail="Service not found")

        service = result["service"]
        if service.user_id != user.id:
            raise HTTPException(status_code=403, detail="You are not allowed to modify this service")

        # Handle image replacement
        if image:
            if image.content_type not in ALLOWED_IMAGE_MIMES:
                raise HTTPException(status_code=400, detail="Unsupported image type")
            new_path = await save_avatar(image)
            service.image = new_path

        update_data = payload.model_dump(exclude_unset=True)
        category_ids = update_data.pop("category_ids", None)
        for k, v in update_data.items():
            setattr(service, k, v)

        return await self.repo.update(service, category_ids)

    async def delete_service(self, service_id: uuid.UUID, user: UserRead) -> None:
        result = await self.repo.get(service_id)
        if not result:
            raise HTTPException(status_code=404, detail="Service not found")
        service = result["service"]
        if service.user_id != user.id:
            raise HTTPException(status_code=403, detail="Not your service")
        await self.repo.delete(service)
