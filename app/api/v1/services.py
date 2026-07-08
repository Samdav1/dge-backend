import json
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession
from app.db.session import get_session
from app.repositories.services_repo import ServiceRepository
from app.services.services_service import ServiceService
from app.schemas.services import ServiceCreate, ServiceRead, ServiceUpdate, ServiceList, ServiceDetailRead
from app.schemas.user import UserRead
from app.dependencies.auth import get_current_user, verify_user_kyc

router = APIRouter(prefix="/services", tags=["services"])


def get_service_service(db: AsyncSession = Depends(get_session)) -> ServiceService:
    repo = ServiceRepository(db)
    return ServiceService(repo)


@router.post("/", response_model=ServiceRead)
async def create_service(
        name: str = Form(...),
        description: str = Form(...),
        price: float = Form(...),
        discount: Optional[bool] = Form(False),
        discount_percent: Optional[float] = Form(0.00),
        service_type: str = Form(...),
        meta_tags: Optional[str] = Form(None),
        keywords: Optional[str] = Form(None),
        category_ids: Optional[str] = Form(None),  # JSON array string or empty
        image: Optional[UploadFile] = File(None),
        db: AsyncSession = Depends(get_session),
        current_user: UserRead = Depends(verify_user_kyc),
        service: ServiceService = Depends(get_service_service),
):
    try:
        from app.models.services import ServiceType  # local import to avoid circulars
        st = ServiceType(service_type)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid service type")

    category_list = None
    if category_ids:
        try:
            parsed = json.loads(category_ids)
            # ensure list of UUIDs
            category_list = [uuid.UUID(str(x)) for x in parsed]
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid category_ids format; must be JSON list of UUIDs")

    payload = ServiceCreate(
        name=name,
        description=description,
        price=price,
        discount=discount,
        discount_percent=discount_percent,
        type=st,
        meta_tags=meta_tags,
        keywords=keywords,
        category_ids=category_list,
    )

    created = await service.create_service(db=db, user=current_user, payload=payload, image=image)
    return created


@router.get("/", response_model=List[ServiceList])
async def list_services(
        status: Optional[str] = None,
        type: Optional[str] = None,
        only_mine: Optional[bool] = False,
        search: Optional[str] = None,
        category_id: Optional[uuid.UUID] = None,
        offset: int = 0,
        limit: int = 100,
        sort_by: str = "newest",
        db: AsyncSession = Depends(get_session),
        current_user: UserRead = Depends(get_current_user),
        service: ServiceService = Depends(get_service_service),
):
    from app.models.services import ServiceStatus, ServiceType  # local import
    status_enum = ServiceStatus(status) if status else None
    type_enum = ServiceType(type) if type else None
    user_id = current_user.id if only_mine else None
    results = await service.list_services(user_id=user_id, status=status_enum, type=type_enum, search=search, category_id=category_id, offset=offset, limit=limit, sort_by=sort_by)
    return results


@router.get("/{service_id}", response_model=ServiceDetailRead)
async def get_service(
        service_id: uuid.UUID,
        service: ServiceService = Depends(get_service_service),
):
    return await service.get_service(service_id)


@router.put("/{service_id}", response_model=ServiceRead)
async def update_service(
        service_id: uuid.UUID,
        name: Optional[str] = Form(None),
        description: Optional[str] = Form(None),
        price: float = Form(...),
        discount: Optional[bool] = Form(False),
        discount_percent: Optional[float] = Form(0.00),
        service_type: Optional[str] = Form(None),
        meta_tags: Optional[str] = Form(None),
        keywords: Optional[str] = Form(None),
        category_ids: Optional[str] = Form(None),
        image: Optional[UploadFile] = File(None),
        db: AsyncSession = Depends(get_session),
        current_user: UserRead = Depends(get_current_user),
        service: ServiceService = Depends(get_service_service),
):
    update_payload = {}
    from app.models.services import ServiceType
    if name is not None:
        update_payload["name"] = name
    if description is not None:
        update_payload["description"] = description
    if price is not None:
        update_payload["price"] = price
    if discount is not None:
        update_payload["discount"] = discount
    if discount_percent is not None:
        update_payload["discount_percent"] = discount_percent
    if service_type is not None:
        try:
            update_payload["type"] = ServiceType(service_type)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid service type")
    if meta_tags is not None:
        update_payload["meta_tags"] = meta_tags
    if keywords is not None:
        update_payload["keywords"] = keywords
    if category_ids:
        try:
            parsed = json.loads(category_ids)
            update_payload["category_ids"] = [uuid.UUID(str(x)) for x in parsed]
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid category_ids format; must be JSON list of UUIDs")

    payload = ServiceUpdate(**update_payload)
    updated = await service.update_service(db=db, service_id=service_id, user=current_user, payload=payload, image=image)
    return updated


@router.delete("/{service_id}", status_code=204)
async def delete_service(
        service_id: uuid.UUID,
        current_user: UserRead = Depends(get_current_user),
        service: ServiceService = Depends(get_service_service),
):
    await service.delete_service(service_id=service_id, user=current_user)
    return None