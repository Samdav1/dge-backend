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
POSTED_JOB_UPLOAD_DIR = "uploaded_files/posted_jobs"
os.makedirs(POSTED_JOB_UPLOAD_DIR, exist_ok=True)
SUBMISSION_UPLOAD_DIR = "uploaded_files/work_submissions"
os.makedirs(SUBMISSION_UPLOAD_DIR, exist_ok=True)

async def scan_file_for_virus(file: UploadFile):
    if not file or not file.filename:
        return
    # Read the first 1MB of the file to check signatures
    content = await file.read(1024 * 1024)
    await file.seek(0)  # Reset pointer for saving later

    # 1. EICAR Standard Antivirus Test File signature check
    if b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*" in content:
        raise HTTPException(
            status_code=400,
            detail="Security scan failed: Malware detected (EICAR signature matched)."
        )

    filename = file.filename.lower()
    dangerous_extensions = {".exe", ".bat", ".sh", ".cmd", ".scr", ".js", ".vbs", ".lnk", ".sys", ".msi"}
    _, ext = os.path.splitext(filename)
    
    # 2. Block dangerous script/executable extensions
    if ext in dangerous_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Security scan failed: Executable file type '{ext}' is blocked to prevent malware execution."
        )

    # 3. Check for double extensions
    if filename.count(".") > 1:
        parts = filename.split(".")
        if parts[-1] in dangerous_extensions or parts[-2] in dangerous_extensions:
            raise HTTPException(
                status_code=400,
                detail="Security scan failed: Double extension with potential malware file detected."
            )

    # 4. Check for MZ header (Windows executable signature)
    if content.startswith(b"MZ"):
        raise HTTPException(
            status_code=400,
            detail="Security scan failed: Windows executable signature (MZ) detected."
        )

    # 5. Check for ELF header (Linux executable signature)
    if content.startswith(b"\x7fELF"):
        raise HTTPException(
            status_code=400,
            detail="Security scan failed: ELF executable signature detected."
        )

async def save_work_submission_file(file: UploadFile, is_image: bool = False) -> str:
    if not file or not file.filename:
        return None

    # Run the virus scan on the uploaded file
    await scan_file_for_virus(file)

    if is_image:
        if not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="Only image files are allowed for image field.")

    extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{extension}"
    file_path = os.path.join(SUBMISSION_UPLOAD_DIR, unique_filename)

    try:
        async with aiofiles.open(file_path, "wb") as f:
            while content := await file.read(1024 * 1024):  # Read in 1MB chunks
                await f.write(content)
    except Exception as e:
        print(f"Error saving submission file: {e}")
        raise HTTPException(status_code=500, detail="Could not save the submission file.")

    return f"/static/work_submissions/{unique_filename}"

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
    if not file or not file.filename:
        return None
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

async def save_posted_job_image(file: UploadFile) -> str:
    """Saves a posted job image to the filesystem."""
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are allowed.")
    extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{extension}"
    file_path = os.path.join(POSTED_JOB_UPLOAD_DIR, unique_filename)

    try:
        async with aiofiles.open(file_path, "wb") as f:
            while content := await file.read(1024 * 1024):
                await f.write(content)
    except Exception:
        raise HTTPException(status_code=500, detail="Could not save the job image file.")
    return f"/static/posted_jobs/{unique_filename}"
