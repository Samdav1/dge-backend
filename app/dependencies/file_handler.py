import os
import uuid
import aiofiles
from fastapi import UploadFile, HTTPException

UPLOAD_DIR = "uploaded_files/avatars"
os.makedirs(UPLOAD_DIR, exist_ok=True)
SERVICE_UPLOAD_DIR = "uploaded_files/services"
os.makedirs(SERVICE_UPLOAD_DIR, exist_ok=True)
KYC_UPLOAD_DIR = "uploaded_files/kyc"
os.makedirs(KYC_UPLOAD_DIR, exist_ok=True)
PORTFOLIO_UPLOAD_DIR = "uploaded_files/portfolio"
os.makedirs(PORTFOLIO_UPLOAD_DIR, exist_ok=True)

async def save_portfolio_media(file: UploadFile) -> str:
    if not file.content_type.startswith("image/") and not file.content_type.startswith("video/"):
        raise HTTPException(status_code=400, detail="Only image and video files are allowed.")

    extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{extension}"
    file_path = os.path.join(PORTFOLIO_UPLOAD_DIR, unique_filename)

    try:
        async with aiofiles.open(file_path, "wb") as f:
            while content := await file.read(1024 * 1024):  # Read in 1MB chunks
                await f.write(content)
    except Exception as e:
        print(f"Error saving file: {e}")
        raise HTTPException(status_code=500, detail="Could not save the portfolio media file.")

    return f"/static/portfolio/{unique_filename}"


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

async def save_service_image(file: UploadFile) -> str:
    """

    :param file:
    :return:
    """
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are allowed.")
    extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{extension}"
    file_path = os.path.join(SERVICE_UPLOAD_DIR, unique_filename)

    try:
        async with aiofiles.open(file_path, "wb") as f:
            while content := await file.read(1024 * 1024):
                await f.write(content)
    except Exception:
        raise HTTPException(status_code=500, detail="Could not save the service file.")
    return f"/static/services/{unique_filename}"

async def delete_service_image(service_image_url: str):
    """Deletes an old service image from the filesystem."""
    if service_image_url:
        filename = os.path.basename(service_image_url)
        file_path = os.path.join(SERVICE_UPLOAD_DIR, filename)
        if os.path.exists(file_path):
            os.remove(file_path)


async def save_kyc_image(file: UploadFile):
    """

    :param file:
    :return:
    """
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are allowed.")

    extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{extension}"
    file_path = os.path.join(KYC_UPLOAD_DIR, unique_filename)

    try:
        async with aiofiles.open(file_path, "wb") as out_file:
            while content := await file.read(1024 * 1024):  # Read 1MB chunks
                await out_file.write(content)

    except Exception as e:
        print(f"Error saving file: {e}")
        raise HTTPException(status_code=500, detail="Could not save the kyc file.")
    return f"/static/kyc/{unique_filename}"

async def delete_kyc_image(service_image_url: str):
    """Deletes an old service image from the filesystem."""
    if service_image_url:
        filename = os.path.basename(service_image_url)
        file_path = os.path.join(KYC_UPLOAD_DIR, filename)
        if os.path.exists(file_path):
            os.remove(file_path)
