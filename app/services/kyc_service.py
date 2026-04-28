from fastapi import HTTPException, UploadFile

from app.repositories import kyc_repo
from app.repositories.kyc_repo import create_user_repo_kyc, update_user_repo_kyc
from sqlmodel.ext.asyncio.session import AsyncSession
from app.schemas.kyc import *
from app.schemas.user import UserRead
from app.dependencies.file_handler import save_kyc_image


async def create_user_kyc_service(db: AsyncSession, kyc: KYCCreate, identification_file: UploadFile) -> KYCRead:
    if not kyc.user_id:
        raise HTTPException(status_code=404, detail="User not found")
    else:
        kyc_location_file = await save_kyc_image(identification_file)
        kyc.id_document_s3_key = kyc_location_file
        user_kyc = await create_user_repo_kyc(db, kyc)
        return user_kyc

async def update_user_service_kyc(db: AsyncSession, user_kyc: KYCUpdate, user_id) -> KYCRead:
    if not user_kyc:
        raise HTTPException(status_code=400, detail="Incomplete data, Missing Entries")
    else:
        try:
            kyc_updated_data = await update_user_repo_kyc(db, user_kyc, user_id)
            kyc_data_refined = KYCRead.model_validate(kyc_updated_data)
            return kyc_data_refined
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"{str(e),}, Error in update_user_repo_kyc")