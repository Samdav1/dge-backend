from fastapi import APIRouter, Depends, HTTPException
from app.dependencies.auth import get_current_user
from app.db.session import get_session
from sqlmodel.ext.asyncio.session import AsyncSession

from app.schemas.kyc import KYCRead, KYCUpdate
from app.services.kyc_service import create_user_kyc_service, update_user_service_kyc
from app.schemas.user import UserRead

router = APIRouter()

@router.post('/create_user_kyc')
async def create_user_kyc(db: AsyncSession = Depends(get_session), current_user: UserRead = Depends(get_current_user))->KYCRead:
    if not current_user.id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    else:
        user_id = current_user.id
        try:
            user_kyc = await create_user_kyc_service(db=db, user_id=user_id)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f" {e}, Unable to create user kyc")
        return user_kyc

@router.patch('/update_user_kyc')
async def update_user_kyc(kyc_data: KYCUpdate, db: AsyncSession = Depends(get_session), current_user: UserRead = Depends(get_current_user)) -> KYCRead:
    if not current_user.id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    else:
        user_id = current_user.id
        try:
            kyc_updated_data = await update_user_service_kyc(db, kyc_data, user_id)
            return kyc_updated_data
        except Exception as e:
            raise HTTPException(status_code=500, detail=f" {e}, Unable to update user kyc")