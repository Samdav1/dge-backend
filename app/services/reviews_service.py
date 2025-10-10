from sqlmodel.ext.asyncio.session import AsyncSession
from fastapi import HTTPException, status
from app.schemas.reviews import ReviewCreate, ReviewUpdate
from app.repositories.reviews_repo import ReviewRepository


class ReviewService:
    @staticmethod
    async def create_review(db: AsyncSession, payload: ReviewCreate):
        new_review = await ReviewRepository.create_review(db, payload)
        await db.commit()
        await db.refresh(new_review)
        return new_review

    @staticmethod
    async def get_review(db: AsyncSession, review_id):
        review = await ReviewRepository.get_review_by_id(db, review_id)
        if not review:
            raise HTTPException(status_code=404, detail="Review not found")
        return review

    @staticmethod
    async def get_reviews_for_portfolio(db: AsyncSession, portfolio_id):
        return await ReviewRepository.get_reviews_for_portfolio(db, portfolio_id)

    @staticmethod
    async def update_review(db: AsyncSession, review_id, payload: ReviewUpdate):
        review = await ReviewRepository.get_review_by_id(db, review_id)
        if not review:
            raise HTTPException(status_code=404, detail="Review not found")
        updated = await ReviewRepository.update_review(db, review, payload)
        await db.commit()
        await db.refresh(updated)
        return updated

    @staticmethod
    async def delete_review(db: AsyncSession, review_id):
        review = await ReviewRepository.get_review_by_id(db, review_id)
        if not review:
            raise HTTPException(status_code=404, detail="Review not found")
        await ReviewRepository.delete_review(db, review)
        await db.commit()
