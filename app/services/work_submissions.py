# app/services/work_submissions.py
from typing import Optional, List
from fastapi import UploadFile, HTTPException
from app.schemas.user import UserRead
from app.schemas.work_submission import WorkSubmissionCreate, WorkSubmissionRead
from app.repositories.work_submissions import WorkSubmissionRepository
from app.dependencies.file_handler import save_avatar  # your file save utility


class WorkSubmissionService:
    def __init__(self, db):
        self.repo = WorkSubmissionRepository(db)

    async def create_work_submission(
        self,
        submission_payload: WorkSubmissionCreate,
        image: Optional[UploadFile],
        files: Optional[UploadFile],
        user: UserRead
    ) -> WorkSubmissionRead:
        # Save files (your save_avatar returns a URL or path)
        image_url = await save_avatar(image) if image else None
        file_url = await save_avatar(files) if files else None

        # Start with payload dict and ensure we set user_id and override file/image urls
        data = submission_payload.model_dump()
        # Remove keys that we will set explicitly to avoid duplicates
        data.pop("file_urls", None)
        data.pop("image_urls", None)
        data.pop("user_id", None)

        # Set the authenticated user
        data["user_id"] = user.id

        if image_url:
            data["image_urls"] = [image_url]
        if file_url:
            data["file_urls"] = [file_url]

        created = WorkSubmissionCreate(**data)
        return await self.repo.create_work_submission(created)

    async def get_work_submission(self, submission_id):
        return await self.repo.get_submission(submission_id)

    async def list_work_submissions(self, user_id: Optional[str] = None):
        return await self.repo.list_submissions(user_id)

    async def update_work_submission(self, submission_id, update_data: dict):
        return await self.repo.update_submission(submission_id, update_data)

    async def delete_work_submission(self, submission_id):
        return await self.repo.delete_submission(submission_id)
