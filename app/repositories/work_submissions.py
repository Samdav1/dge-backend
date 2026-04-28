# app/repositories/work_submissions.py
from typing import List, Optional
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.work_submissions import WorkSubmission
from app.schemas.work_submission import WorkSubmissionCreate, WorkSubmissionRead

class WorkSubmissionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_work_submission(self, create: WorkSubmissionCreate) -> WorkSubmissionRead:
        new_submission = WorkSubmission(**create.model_dump())
        self.db.add(new_submission)
        try:
            await self.db.commit()
            await self.db.refresh(new_submission)
        except Exception as e:
            await self.db.rollback()
            raise HTTPException(status_code=500, detail=f"Error creating submission: {str(e)}")
        return WorkSubmissionRead.model_validate(new_submission)

    async def get_submission(self, submission_id: UUID) -> WorkSubmissionRead:
        q = await self.db.execute(select(WorkSubmission).where(WorkSubmission.id == submission_id))
        submission = q.scalar_one_or_none()
        if not submission:
            raise HTTPException(status_code=404, detail="Submission not found")
        return WorkSubmissionRead.model_validate(submission)

    async def list_submissions(self, user_id: Optional[UUID] = None) -> List[WorkSubmissionRead]:
        q = select(WorkSubmission)
        if user_id:
            q = q.where(WorkSubmission.user_id == user_id)
        q = q.order_by(WorkSubmission.created_at.desc())
        result = await self.db.execute(q)
        items = result.scalars().all()
        return [WorkSubmissionRead.model_validate(i) for i in items]

    async def update_submission(self, submission_id: UUID, update_data: dict) -> WorkSubmissionRead:
        q = await self.db.execute(select(WorkSubmission).where(WorkSubmission.id == submission_id))
        submission = q.scalar_one_or_none()
        if not submission:
            raise HTTPException(status_code=404, detail="Submission not found")

        for k, v in update_data.items():
            setattr(submission, k, v)

        try:
            await self.db.commit()
            await self.db.refresh(submission)
        except Exception as e:
            await self.db.rollback()
            raise HTTPException(status_code=500, detail=f"Error updating submission: {str(e)}")
        return WorkSubmissionRead.model_validate(submission)

    async def delete_submission(self, submission_id: UUID):
        q = await self.db.execute(select(WorkSubmission).where(WorkSubmission.id == submission_id))
        submission = q.scalar_one_or_none()
        if not submission:
            raise HTTPException(status_code=404, detail="Submission not found")

        await self.db.delete(submission)
        try:
            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            raise HTTPException(status_code=500, detail=f"Error deleting submission: {str(e)}")
        return {"message": "Submission deleted successfully"}
