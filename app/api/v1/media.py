from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from app.dependencies.auth import get_current_user
from app.dependencies.file_handler import save_posted_job_image
from app.schemas.user import UserRead

router = APIRouter()

@router.post("/upload/job-image")
async def upload_job_image(
    file: UploadFile = File(...),
    current_user: UserRead = Depends(get_current_user)
):
    """Upload an image for a posted job."""
    try:
        url = await save_posted_job_image(file)
        return {"url": url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
