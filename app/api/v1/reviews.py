from fastapi import APIRouter, Depends, status, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession
from uuid import UUID
from typing import List
from app.db.session import get_session
from app.schemas.reviews import ReviewCreate, ReviewRead, ReviewUpdate
from app.services.reviews_service import ReviewService
from app.dependencies.auth import get_current_user
from app.schemas.user import UserRead

router = APIRouter(prefix="/reviews")


@router.post("/", response_model=ReviewRead, status_code=status.HTTP_201_CREATED)
async def create_review(payload: ReviewCreate, db: AsyncSession = Depends(get_session),
                        current_user: UserRead = Depends(get_current_user)):
    payload.user_id = current_user.id
    return await ReviewService.create_review(db, payload)


@router.get("/{review_id}", response_model=ReviewRead)
async def get_review(review_id: UUID, db: AsyncSession = Depends(get_session),
                     current_user: UserRead = Depends(get_current_user)
                     ):
    return await ReviewService.get_review(db, review_id)


@router.get("/portfolio/{portfolio_id}", response_model=List[ReviewRead])
async def get_reviews_for_portfolio(portfolio_id: UUID, db: AsyncSession = Depends(get_session),
                                    current_user: UserRead = Depends(get_current_user)
                                    ):
    return await ReviewService.get_reviews_for_portfolio(db, portfolio_id)


@router.put("/{review_id}", response_model=ReviewRead)
async def update_review(review_id: UUID, payload: ReviewUpdate,
                        db: AsyncSession = Depends(get_session), current_user: UserRead = Depends(get_current_user)
                        ):
    return await ReviewService.update_review(db, review_id, payload)


@router.delete("/{review_id}")
async def delete_review(review_id: UUID,
                        db: AsyncSession = Depends(get_session), current_user: UserRead = Depends(get_current_user)
                        ):
    await ReviewService.delete_review(db, review_id)
    return {"detail": "Review deleted successfully"}
