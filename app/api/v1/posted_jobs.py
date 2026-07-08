import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from app.db.session import get_session
from app.dependencies.auth import get_current_user, verify_user_kyc
from app.schemas.posted_job import PostedJobCreate, PostedJobRead, PostedJobUpdate
from app.schemas.price_negotiation import PriceNegotiationRead, PriceNegotiationCreate
from app.schemas.user import UserRead
from app.repositories.posted_job_repo import PostedJobRepository
from app.services.posted_job_service import PostedJobService

router = APIRouter()


def get_service(db: AsyncSession = Depends(get_session)) -> PostedJobService:
    return PostedJobService(PostedJobRepository(db), db)


@router.post("/", response_model=PostedJobRead)
async def create_posted_job(
    payload: PostedJobCreate,
    user: UserRead = Depends(verify_user_kyc),
    service: PostedJobService = Depends(get_service),
):
    """Post a new help request / job. Requires wallet balance >= max_price_cents."""
    return await service.create_posted_job(payload, user.id)


@router.get("/", response_model=List[PostedJobRead])
async def list_open_jobs(
    category_id: Optional[uuid.UUID] = None,
    search: Optional[str] = None,
    service: PostedJobService = Depends(get_service),
):
    """List all open posted jobs (public marketplace feed — no auth required)."""
    return await service.list_open_jobs(category_id=category_id, search=search)


@router.get("/me", response_model=List[PostedJobRead])
async def list_my_jobs(
    user: UserRead = Depends(get_current_user),
    service: PostedJobService = Depends(get_service),
):
    """List all jobs posted by the current user."""
    return await service.list_my_jobs(user.id)


@router.get("/{job_id}", response_model=PostedJobRead)
async def get_posted_job(
    job_id: uuid.UUID,
    service: PostedJobService = Depends(get_service),
):
    """Get a single posted job by ID (public — no auth required)."""
    return await service.get_job(job_id)


@router.get("/{job_id}/bids", response_model=List[PriceNegotiationRead])
async def get_job_bids(
    job_id: uuid.UUID,
    user: UserRead = Depends(get_current_user),
    service: PostedJobService = Depends(get_service),
):
    """Get all bids (negotiations) on a posted job. Only visible to the job poster."""
    return await service.get_job_bids(job_id, user.id)


@router.delete("/{job_id}", response_model=PostedJobRead)
async def cancel_posted_job(
    job_id: uuid.UUID,
    user: UserRead = Depends(get_current_user),
    service: PostedJobService = Depends(get_service),
):
    """Cancel an open posted job."""
    return await service.cancel_job(job_id, user.id)
