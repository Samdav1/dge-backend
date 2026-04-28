from fastapi import APIRouter, Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List
import uuid
from app.db.session import get_session

from app.schemas.price_negotiation import (
    PriceNegotiationCreate,
    PriceNegotiationUpdate,
    PriceNegotiationRead,
)
from app.services.price_negotiation_service import PriceNegotiationService
from app.repositories.price_negotiation_repo import PriceNegotiationRepository
from app.dependencies.auth import get_current_user
from app.schemas.user import UserRead

router = APIRouter()

@router.post("/", response_model=PriceNegotiationRead)
async def create_negotiation(
    payload: PriceNegotiationCreate,
    user: UserRead = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    service = PriceNegotiationService(PriceNegotiationRepository(db))
    return await service.create(payload, user.id)

@router.get("/", response_model=List[PriceNegotiationRead])
async def get_my_negotiations(
    user: UserRead = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    service = PriceNegotiationService(PriceNegotiationRepository(db))
    return await service.get_for_user(user.id)

@router.patch("/{negotiation_id}", response_model=PriceNegotiationRead)
async def update_negotiation(
    negotiation_id: uuid.UUID,
    payload: PriceNegotiationUpdate,
    current_user: UserRead = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    service = PriceNegotiationService(PriceNegotiationRepository(db))
    try:
        return await service.update(negotiation_id, payload, db, current_user)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))