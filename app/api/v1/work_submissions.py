from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_session
from app.dependencies.auth import get_current_user
from app.schemas.user import UserRead
from app.schemas.work_submission import WorkSubmissionCreate, WorkSubmissionRead
from app.services.work_submissions import WorkSubmissionService

router = APIRouter(prefix="/work_submissions",)


@router.post("/", response_model=WorkSubmissionRead)
async def create_work_submission(
        form: WorkSubmissionCreate = Depends(WorkSubmissionCreate.as_form),
        image: Optional[UploadFile] = File(None),
        files: Optional[UploadFile] = File(None),
        db: AsyncSession = Depends(get_session),
        user: UserRead = Depends(get_current_user)
):
    """

    :param form:
    :param image:
    :param files:
    :param db:
    :param user:
    :return:
    """
    service = WorkSubmissionService(db)
    return await service.create_work_submission(form, image=image, files=files, user=user)


@router.get("/", response_model=List[WorkSubmissionRead])
async def list_submissions(
        db: AsyncSession = Depends(get_session),
        user: UserRead = Depends(get_current_user)
):
    """

    :param db:
    :param user:
    :return:
    """
    service = WorkSubmissionService(db)
    return await service.list_work_submissions(user_id=user.id)


@router.get("/{submission_id}", response_model=WorkSubmissionRead)
async def get_submission(
        submission_id: UUID,
        db: AsyncSession = Depends(get_session),
        user: UserRead = Depends(get_current_user)
):
    """

    :param submission_id:
    :param db:
    :param user:
    :return:
    """
    service = WorkSubmissionService(db)
    return await service.get_work_submission(submission_id)


@router.put("/{submission_id}", response_model=WorkSubmissionRead)
async def update_submission(
        submission_id: UUID,
        text: Optional[str] = Depends(lambda: None),  # simpler: use Form/Body as needed
        links: Optional[str] = Depends(lambda: None),
        db: AsyncSession = Depends(get_session),
        user: UserRead = Depends(get_current_user)
):
    """

    :param submission_id:
    :param text:
    :param links:
    :param db:
    :param user:
    :return:
    """
    # parse links if provided (assume JSON or CSV)
    parsed_links = None
    if links:
        import json
        try:
            parsed_links = json.loads(links)
        except Exception:
            parsed_links = [x.strip() for x in links.split(",") if x.strip()]

    update_data = {}
    if text is not None:
        update_data["text"] = text
    if parsed_links is not None:
        update_data["links"] = parsed_links

    service = WorkSubmissionService(db)
    return await service.update_work_submission(submission_id, update_data)


@router.delete("/{submission_id}")
async def delete_submission(
        submission_id: UUID,
        db: AsyncSession = Depends(get_session),
        user: UserRead = Depends(get_current_user)
):
    """

    :param submission_id:
    :param db:
    :param user:
    :return:
    """
    service = WorkSubmissionService(db)
    return await service.delete_work_submission(submission_id)