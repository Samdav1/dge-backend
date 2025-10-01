import os
import uuid
import aiofiles
from fastapi import UploadFile, HTTPException

UPLOAD_DIR = "uploaded_files/avatars"
os.makedirs(UPLOAD_DIR, exist_ok=True)


async def save_avatar(file: UploadFile) -> str:
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are allowed.")

    extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{extension}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    try:
        async with aiofiles.open(file_path, "wb") as f:
            while content := await file.read(1024 * 1024):  # Read in 1MB chunks
                await f.write(content)
    except Exception:
        raise HTTPException(status_code=500, detail="Could not save the avatar file.")

    return f"/static/avatars/{unique_filename}"


async def delete_avatar(avatar_url: str):
    """Deletes an old avatar file from the filesystem."""
    if avatar_url:
        # Convert URL path to system file path
        filename = os.path.basename(avatar_url)
        file_path = os.path.join(UPLOAD_DIR, filename)
        if os.path.exists(file_path):
            os.remove(file_path)