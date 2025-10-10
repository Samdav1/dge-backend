from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List
import uuid
from app.db.session import get_session
from app.dependencies.auth import get_current_user
from app.schemas.escrow import EscrowCreate, EscrowRead, EscrowActionResponse
from app.schemas.user import UserRead
from app.services.escrow_service import EscrowService

router = APIRouter(prefix="/escrows",)


def get_escrow_service(db: AsyncSession = Depends(get_session)):
    return EscrowService(db)


@router.post("/", response_model=EscrowRead, status_code=status.HTTP_201_CREATED)
async def create_escrow(
    payload: EscrowCreate,
    current_user: UserRead = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
    service: EscrowService = Depends(get_escrow_service),
):
    try:
        escrow = await service.create_escrow(current_user, payload)
        return escrow
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.get("/{escrow_id}", response_model=EscrowRead)
async def get_escrow(
    escrow_id: uuid.UUID,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
    service: EscrowService = Depends(get_escrow_service),
):
    escrow = await service.repo.get_by_id(escrow_id)
    if not escrow:
        raise HTTPException(status_code=404, detail="Escrow not found")
    # optional: check access — only participants can read
    return escrow


@router.post("/{escrow_id}/release", response_model=EscrowActionResponse)
async def release_escrow(
    escrow_id: uuid.UUID,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
    service: EscrowService = Depends(get_escrow_service),
):
    try:
        escrow = await service.release_escrow(current_user, escrow_id)
        return EscrowActionResponse(id=escrow.id, status=escrow.status, message="Escrow released")
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{escrow_id}/refund", response_model=EscrowActionResponse)
async def refund_escrow(
    escrow_id: uuid.UUID,
    current_user = Depends(get_current_user),
    service: EscrowService = Depends(get_escrow_service),
):
    try:
        escrow = await service.refund_escrow(current_user, escrow_id)
        return EscrowActionResponse(id=escrow.id, status=escrow.status, message="Escrow refunded")
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{escrow_id}/dispute", response_model=EscrowActionResponse)
async def dispute_escrow(
    escrow_id: uuid.UUID,
    current_user = Depends(get_current_user),
    service: EscrowService = Depends(get_escrow_service),
):
    try:
        escrow = await service.dispute_escrow(current_user, escrow_id)
        return EscrowActionResponse(id=escrow.id, status=escrow.status, message="Escrow disputed")
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[EscrowRead])
async def list_my_escrows(
    current_user = Depends(get_current_user),
    service: EscrowService = Depends(get_escrow_service),
):
    results = await service.repo.list_for_user(current_user.id)
    return results