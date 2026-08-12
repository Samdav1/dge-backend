import hmac
import hashlib
import time
import json
import logging
from typing import Optional, Dict, Any
import httpx
from app.config import settings

logger = logging.getLogger(__name__)


def create_sumsub_signature(
    secret_key: str,
    ts: str,
    method: str,
    path_with_query: str,
    body: bytes = b""
) -> str:
    """
    Generate HMAC-SHA256 signature for Sumsub API requests.
    Signature string format: timestamp + HTTPMethod + pathWithQuery + body
    """
    msg = ts.encode('utf-8') + method.upper().encode('utf-8') + path_with_query.encode('utf-8') + body
    return hmac.new(secret_key.encode('utf-8'), msg, hashlib.sha256).hexdigest()


def verify_sumsub_webhook_signature(
    body: bytes,
    digest_header: Optional[str],
    secret_key: str
) -> bool:
    """
    Verify HMAC-SHA256 signature for incoming Sumsub webhooks.
    """
    if not secret_key:
        logger.warning("SUMSUB_WEBHOOK_SECRET/SUMSUB_SECRET_KEY is not configured; skipping signature check.")
        return True

    if not digest_header:
        return False

    computed = hmac.new(secret_key.encode('utf-8'), body, hashlib.sha256).hexdigest()
    # Check against digest header (which might be raw hex or contain algorithm prefix)
    clean_digest = digest_header.strip()
    if clean_digest.startswith("HMAC_SHA256="):
        clean_digest = clean_digest[12:]

    return hmac.compare_digest(computed.lower(), clean_digest.lower())


async def generate_sumsub_access_token(
    user_id: str,
    level_name: Optional[str] = None,
    ttl_in_sec: int = 1800
) -> Dict[str, Any]:
    """
    Generate a Sumsub WebSDK access token for a given user ID.
    API endpoint: POST /resources/accessTokens?userId={user_id}&ttlInSec={ttl}&levelName={level}
    """
    app_token = settings.sumsub_app_token
    secret_key = settings.sumsub_secret_key
    base_url = settings.sumsub_base_url.rstrip("/")
    level = level_name or settings.sumsub_level_name or "basic-kyc-level"

    if not app_token or not secret_key:
        logger.warning("SUMSUB_APP_TOKEN or SUMSUB_SECRET_KEY not configured, returning dev token.")
        return {
            "token": f"dev_token_{user_id}",
            "userId": user_id,
            "levelName": level
        }

    path_with_query = f"/resources/accessTokens?userId={user_id}&ttlInSec={ttl_in_sec}&levelName={level}"
    url = f"{base_url}{path_with_query}"

    ts = str(int(time.time()))
    sig = create_sumsub_signature(secret_key, ts, "POST", path_with_query, b"")

    headers = {
        "Accept": "application/json",
        "X-App-Token": app_token,
        "X-App-Access-Sig": sig,
        "X-App-Access-Ts": ts
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, headers=headers)
            if resp.status_code != 200:
                logger.error(f"Sumsub access token request failed [{resp.status_code}]: {resp.text}")
                raise Exception(f"Sumsub API returned status code {resp.status_code}: {resp.text}")
            
            data = resp.json()
            return {
                "token": data.get("token"),
                "userId": user_id,
                "levelName": level
            }
    except Exception as e:
        logger.error(f"Error generating Sumsub access token for user {user_id}: {e}")
        raise e


async def check_and_sync_sumsub_applicant_status(db: Any, kyc_record: Any) -> None:
    """
    Directly query Sumsub API for applicant verification status using externalUserId.
    Updates the database KYC record if a decision (GREEN/RED/completed) is returned.
    """
    app_token = settings.sumsub_app_token
    secret_key = settings.sumsub_secret_key
    if not app_token or not secret_key or not kyc_record or not kyc_record.user_id:
        return

    from app.models.kyc import KYCStatus
    user_id_str = str(kyc_record.user_id)
    base_url = settings.sumsub_base_url.rstrip("/")
    path_with_query = f"/resources/applicants/-;externalUserId={user_id_str}/one"
    url = f"{base_url}{path_with_query}"

    ts = str(int(time.time()))
    sig = create_sumsub_signature(secret_key, ts, "GET", path_with_query, b"")

    headers = {
        "Accept": "application/json",
        "X-App-Token": app_token,
        "X-App-Access-Sig": sig,
        "X-App-Access-Ts": ts
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                decision = parse_sumsub_decision(data)
                
                new_status_str = decision.get("status")
                if new_status_str == "verified":
                    kyc_record.status = KYCStatus.verified
                    kyc_record.rejection_reason = None
                elif new_status_str == "rejected":
                    kyc_record.status = KYCStatus.rejected
                    kyc_record.rejection_reason = decision.get("rejectionReason") or "Verification rejected"
                elif new_status_str == "unverified":
                    kyc_record.status = KYCStatus.unverified
                elif new_status_str == "pending":
                    kyc_record.status = KYCStatus.pending
                
                if decision.get("applicantId"):
                    kyc_record.sumsub_applicant_id = decision.get("applicantId")
                if decision.get("inspectionId"):
                    kyc_record.sumsub_inspection_id = decision.get("inspectionId")
                
                kyc_record.kyc_provider = "sumsub"
                db.add(kyc_record)
                await db.commit()
                await db.refresh(kyc_record)
    except Exception as e:
        logger.error(f"Error syncing Sumsub applicant status for user {user_id_str}: {e}")


def parse_sumsub_decision(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse decision details from a Sumsub webhook payload OR GET applicant API response safely.
    Handles both top-level webhook fields and nested `review` object fields returned by Sumsub API.
    """
    review_obj = payload.get("review") if isinstance(payload.get("review"), dict) else {}

    event_type = payload.get("type") or payload.get("eventName")
    review_status = payload.get("reviewStatus") or review_obj.get("reviewStatus")
    
    review_result = payload.get("reviewResult") or review_obj.get("reviewResult") or {}
    if not isinstance(review_result, dict):
        review_result = {}
    
    review_answer = review_result.get("reviewAnswer")  # "GREEN" or "RED"
    reject_labels = review_result.get("rejectLabels") or []
    reject_type = review_result.get("reviewRejectType")

    applicant_id = payload.get("applicantId") or payload.get("id")
    inspection_id = payload.get("inspectionId") or review_obj.get("inspectionId")
    external_user_id = payload.get("externalUserId") or payload.get("userId") or payload.get("applicantMemberId")

    status = "pending"
    rejection_reason = None

    if review_answer == "GREEN":
        status = "verified"
    elif review_answer == "RED":
        status = "rejected"
        if isinstance(reject_labels, list) and len(reject_labels) > 0:
            rejection_reason = ", ".join([str(l).replace("_", " ").title() for l in reject_labels])
        else:
            rejection_reason = payload.get("reason") or "Identity verification failed on Sumsub."
        if reject_type:
            rejection_reason += f" ({reject_type.capitalize()})"
    elif review_status == "completed":
        status = "verified"
    elif review_status == "init":
        status = "unverified"
    elif review_status in ["pending", "queued", "onHold", "prechecked"]:
        status = "pending"

    return {
        "status": status,
        "externalUserId": external_user_id,
        "applicantId": applicant_id,
        "inspectionId": inspection_id,
        "rejectionReason": rejection_reason,
        "eventType": event_type,
        "reviewAnswer": review_answer,
        "reviewStatus": review_status
    }
