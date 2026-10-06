from fastapi import APIRouter, Depends, status
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List
from app.db.session import get_session
from app.schemas.permission import PermissionCreate, PermissionRead, PermissionUpdate
from app.services.permission_service import PermissionService
from app.dependencies.auth import get_current_user  # your JWT session dependency

router = APIRouter(prefix="/permissions", )


@router.get("/", response_model=List[PermissionRead])
async def list_permissions(
    db: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user),
)   :
    service = PermissionService(db)
    return await service.list_permissions()


@router.get("/{permission_id}", response_model=PermissionRead)
async def get_permission(
    permission_id: str,
    db: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user),
    ):
    service = PermissionService(db)
    return await service.get_permission(permission_id)


@router.post("/", response_model=PermissionRead, status_code=status.HTTP_201_CREATED)
async def create_permission(
    payload: PermissionCreate,
    db: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user),
    ):
    service = PermissionService(db)
    return await service.create_permission(payload)


@router.put("/{permission_id}", response_model=PermissionRead)
async def update_permission(
    permission_id: str,
    payload: PermissionUpdate,
    db: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user),
    ):
    service = PermissionService(db)
    return await service.update_permission(permission_id, payload)


@router.delete("/{permission_id}")
async def delete_permission(
    permission_id: str,
    db: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user),
    ):
    service = PermissionService(db)
    await service.delete_permission(permission_id)
    return {"message": "Permission deleted successfully"}