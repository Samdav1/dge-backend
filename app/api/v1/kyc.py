from fastapi import APIRouter, Depends, HTTPException, UploadFile, Form, File
from app.dependencies.auth import get_current_user
from app.db.session import get_session
from sqlmodel.ext.asyncio.session import AsyncSession

from app.schemas.kyc import KYCRead, KYCUpdate, KYCCreate, DocumentType, KYCStatus
from app.services.kyc_service import create_user_kyc_service, update_user_service_kyc, get_user_kyc_service
from app.schemas.user import UserRead

router = APIRouter()

@router.post('/create_user_kyc')
async def create_user_kyc(
        verification_file: UploadFile = File(...),
        id_type: DocumentType = Form(...),
        id_value: str = Form(...),
        db: AsyncSession = Depends(get_session),
        current_user: UserRead = Depends(get_current_user)
)->KYCRead:

    if not current_user.id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    else:
        user_id = current_user.id
        try:
            new_kyc = KYCCreate(id_document_type=id_type, id_document_value=id_value, user_id=user_id, status=KYCStatus.pending)
            user_kyc = await create_user_kyc_service(db=db, kyc=new_kyc, identification_file=verification_file)
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

@router.get('/get_user_kyc', response_model=KYCRead | None)
async def get_user_kyc(db: AsyncSession = Depends(get_session), current_user: UserRead = Depends(get_current_user)):
    if not current_user.id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        return await get_user_kyc_service(db, current_user.id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f" {e}, Unable to fetch user kyc")


import hmac
import hashlib
import json
import uuid
from datetime import datetime, timezone
from fastapi import Request
from app.models.kyc import KYC, KYCStatus
from sqlmodel import select

def verify_metamap_signature(payload: bytes, signature: str, secret: str) -> bool:
    if not secret:
        return True
    computed = hmac.new(secret.encode('utf-8'), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(computed, signature)

@router.post('/webhooks/metamap')
async def metamap_webhook(request: Request, db: AsyncSession = Depends(get_session)):
    signature = request.headers.get("x-signature")
    body = await request.body()
    
    from app.config import settings
    # Validate HMAC signature for all incoming MetaMap webhooks
    if settings.metamap_webhook_secret:
        if not signature:
            raise HTTPException(status_code=401, detail="Missing MetaMap webhook signature")
        if not verify_metamap_signature(body, signature, settings.metamap_webhook_secret):
            raise HTTPException(status_code=401, detail="Invalid MetaMap signature")
            
    try:
        payload = json.loads(body)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
        
    event_name = payload.get("eventName")
    # MetaMap event name is verification_completed
    if event_name and event_name != "verification_completed":
        return {"status": "ignored", "event": event_name}
        
    status = payload.get("status")
    metadata = payload.get("metadata", {})
    user_id_str = metadata.get("userId")
    
    if not user_id_str:
        user_id_str = payload.get("userId") or payload.get("resourceId") or metadata.get("user_id")
        
    if not user_id_str:
        raise HTTPException(status_code=400, detail="Missing userId in metadata")
        
    try:
        uid = uuid.UUID(user_id_str)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid userId UUID format")
        
    stmt = select(KYC).where(KYC.user_id == uid)
    res = await db.execute(stmt)
    kyc_record = res.scalar_one_or_none()
    
    kyc_status = KYCStatus.rejected
    if status in ["verified", "success", "approved"]:
        kyc_status = KYCStatus.verified
    elif status in ["pending", "review"]:
        kyc_status = KYCStatus.pending
    else:
        kyc_status = KYCStatus.rejected
        
    if not kyc_record:
        kyc_record = KYC(
            user_id=uid,
            status=kyc_status,
            metamap_verification_id=payload.get("verificationId"),
            metamap_flow_id=payload.get("flowId"),
            rejection_reason=payload.get("rejectionReason") or payload.get("reason") if kyc_status == KYCStatus.rejected else None,
            submitted_at=datetime.now(timezone.utc)
        )
        db.add(kyc_record)
    else:
        kyc_record.status = kyc_status
        kyc_record.metamap_verification_id = payload.get("verificationId") or kyc_record.metamap_verification_id
        kyc_record.metamap_flow_id = payload.get("flowId") or kyc_record.metamap_flow_id
        if kyc_status == KYCStatus.rejected:
            kyc_record.rejection_reason = payload.get("rejectionReason") or payload.get("reason") or "MetaMap verification failed"
        else:
            kyc_record.rejection_reason = None
        db.add(kyc_record)
        
    await db.commit()
    return {"status": "success", "kyc_status": kyc_status.value}


@router.get('/config')
async def get_kyc_config(db: AsyncSession = Depends(get_session)):
    """
    Get active platform KYC configuration (provider: 'sumsub' or 'metamap').
    """
    from app.models.admin import AdminKYCSettings
    from app.config import settings

    try:
        stmt = select(AdminKYCSettings).where(AdminKYCSettings.id == 1)
        res = await db.execute(stmt)
        kyc_settings = res.scalar_one_or_none()
        active_provider = kyc_settings.active_provider if kyc_settings else settings.default_kyc_provider
    except Exception:
        active_provider = settings.default_kyc_provider

    return {
        "active_provider": active_provider or "sumsub",
        "metamap_client_id": settings.metamap_client_id,
        "sumsub_level_name": settings.sumsub_level_name
    }


@router.post('/sumsub-token')
async def get_sumsub_token(
    current_user: UserRead = Depends(get_current_user)
):
    """
    Generate a Sumsub WebSDK access token for the logged-in user.
    """
    if not current_user or not current_user.id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    from app.services.sumsub_service import generate_sumsub_access_token
    try:
        token_data = await generate_sumsub_access_token(user_id=str(current_user.id))
        return token_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unable to generate Sumsub access token: {e}")


@router.post('/webhooks/sumsub')
async def sumsub_webhook(request: Request, db: AsyncSession = Depends(get_session)):
    """
    Sumsub Webhook Endpoint for status and decision updates.
    """
    from app.config import settings
    from app.services.sumsub_service import verify_sumsub_webhook_signature, parse_sumsub_decision

    body = await request.body()
    digest_header = request.headers.get("x-payload-digest") or request.headers.get("x-payload-digest-hex")

    secret = settings.sumsub_webhook_secret or settings.sumsub_secret_key
    if secret:
        if not verify_sumsub_webhook_signature(body, digest_header, secret):
            raise HTTPException(status_code=401, detail="Invalid Sumsub webhook signature")

    try:
        payload = json.loads(body)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    decision = parse_sumsub_decision(payload)
    ext_user_id_str = decision.get("externalUserId")

    if not ext_user_id_str:
        return {"status": "ignored", "reason": "No externalUserId/userId in payload"}

    try:
        uid = uuid.UUID(str(ext_user_id_str))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid externalUserId UUID format")

    stmt = select(KYC).where(KYC.user_id == uid)
    res = await db.execute(stmt)
    kyc_record = res.scalar_one_or_none()

    new_status = decision.get("status")
    status_enum = KYCStatus.pending
    if new_status == "verified":
        status_enum = KYCStatus.verified
    elif new_status == "rejected":
        status_enum = KYCStatus.rejected
    else:
        status_enum = KYCStatus.pending

    rejection_reason = decision.get("rejectionReason")

    if not kyc_record:
        kyc_record = KYC(
            user_id=uid,
            status=status_enum,
            sumsub_applicant_id=decision.get("applicantId"),
            sumsub_inspection_id=decision.get("inspectionId"),
            kyc_provider="sumsub",
            rejection_reason=rejection_reason if status_enum == KYCStatus.rejected else None,
            submitted_at=datetime.now(timezone.utc)
        )
        db.add(kyc_record)
    else:
        kyc_record.status = status_enum
        kyc_record.kyc_provider = "sumsub"
        if decision.get("applicantId"):
            kyc_record.sumsub_applicant_id = decision.get("applicantId")
        if decision.get("inspectionId"):
            kyc_record.sumsub_inspection_id = decision.get("inspectionId")

        if status_enum == KYCStatus.rejected:
            kyc_record.rejection_reason = rejection_reason or "Sumsub verification failed"
        elif status_enum == KYCStatus.verified:
            kyc_record.rejection_reason = None

        db.add(kyc_record)

    await db.commit()
    return {
        "status": "success",
        "kyc_status": status_enum.value,
        "user_id": str(uid)
    }