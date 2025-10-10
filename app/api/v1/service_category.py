from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
import uuid
from typing import List
from app.db.session import get_session
from sqlmodel.ext.asyncio.session import AsyncSession
from app.schemas.service_category import (
    ServiceCategoryCreate, ServiceCategoryRead, ServiceCategoryUpdate,
    ServiceCategoryLinkCreate, ServiceCategoryLinkRead
)
from app.services.service_category_service import (
    ServiceCategoryService, ServiceCategoryLinkService
)

router = APIRouter(prefix="/categories")


# ---- ServiceCategory Endpoints ----
@router.post("/", response_model=ServiceCategoryRead, status_code=status.HTTP_201_CREATED)
async def create_category(
    data: ServiceCategoryCreate,
    session: AsyncSession = Depends(get_session)
):
    return await ServiceCategoryService(session).create_category(data)


@router.get("/", response_model=List[ServiceCategoryRead])
async def list_categories(session: AsyncSession = Depends(get_session)):
    return await ServiceCategoryService(session).get_all_categories()


@router.get("/{category_id}", response_model=ServiceCategoryRead)
async def get_category(category_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    category = await  ServiceCategoryService(session).get_category(category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


@router.put("/{category_id}", response_model=ServiceCategoryRead)
async def update_category(category_id: uuid.UUID, data: ServiceCategoryUpdate, session: AsyncSession = Depends(get_session)):
    category = await ServiceCategoryService(session).update_category(category_id, data)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(category_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    success = await ServiceCategoryService(session).delete_category(category_id)
    if not success:
        raise HTTPException(status_code=404, detail="Category not found")
    return None


# ---- ServiceCategoryLink Endpoints ----
@router.post("/link", response_model=ServiceCategoryLinkRead, status_code=status.HTTP_201_CREATED)
async def create_link(data: ServiceCategoryLinkCreate, session: StopAsyncIteration = Depends(get_session)):
    return await ServiceCategoryLinkService(session).create_link(data)


@router.get("/service/{service_id}/links", response_model=List[ServiceCategoryLinkRead])
async def list_links(service_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    return await ServiceCategoryLinkService(session).get_links_for_service(service_id)
