from dotenv import unset_key
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from fastapi import HTTPException
from app.models.kyc import KYC
from app.schemas.kyc import KYCStatus, KYCRead, KYCCreate, KYCUpdate

async def create_user_repo_kyc(db: AsyncSession, kyc_userid) ->KYCRead:
    if not kyc_userid:
        raise HTTPException(status_code=404, detail="User not found")
    user_kyc = KYC(user_id=kyc_userid)
    try:
        db.add(user_kyc)
        await db.commit()
        await db.refresh(user_kyc)
        kyc_refined = KYCRead.model_validate(user_kyc)
        return kyc_refined
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

async def update_user_repo_kyc(db: AsyncSession, kyc_update: KYCUpdate, user_id ) ->KYCRead:
    if not kyc_update:
        raise HTTPException(status_code=400, detail="Incomplete data, Missing Entries")
    else:
        statement = select(KYC).where(KYC.user_id == user_id)
        result = await db.exec(statement)
        kyc_user_result = result.first()
        result_dump = kyc_update.model_dump(exclude_unset=True)
        for key, value in result_dump.items():
            if hasattr(kyc_update, key):
                setattr(kyc_user_result, key, value)

        try:
            db.add(kyc_user_result)
            await db.commit()
            await db.refresh(kyc_user_result)
            kyc_refined = KYCRead.model_validate(kyc_user_result)
            return kyc_refined
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"{str(e),}, Error in update_user_repo_kyc")