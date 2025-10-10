from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from app.models.portfolio import Review
from app.schemas.reviews import ReviewCreate, ReviewUpdate
from typing import List, Optional
import uuid


class ReviewRepository:
    @staticmethod
    async def create_review(db: AsyncSession, data: ReviewCreate) -> Review:
        review = Review(**data.model_dump())
        db.add(review)
        return review  # No commit here

    @staticmethod
    async def get_review_by_id(db: AsyncSession, review_id: uuid.UUID) -> Optional[Review]:
        query = select(Review).where(Review.id == review_id)
        result = await db.exec(query)
        return result.first()

    @staticmethod
    async def get_reviews_for_portfolio(db: AsyncSession, portfolio_id: uuid.UUID) -> List[Review]:
        query = select(Review).where(Review.portfolio_id == portfolio_id)
        result = await db.exec(query)
        return result.all()

    @staticmethod
    async def update_review(db: AsyncSession, review: Review, data: ReviewUpdate) -> Review:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(review, field, value)
        return review

    @staticmethod
    async def delete_review(db: AsyncSession, review: Review) -> None:
        await db.delete(review)
