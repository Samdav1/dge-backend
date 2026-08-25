# app/api/v1/superadmin.py
from fastapi import APIRouter, Depends, UploadFile, Form, status, Response, HTTPException, Request
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import Optional, List
import uuid
from datetime import datetime, timezone

from watchfiles.run import get_tty_path

from app.core.security import get_access_token, get_refresh_token
from app.dependencies.admin_auth import get_current_admin
from app.services.super_admin_service import SuperAdminService
from app.models.admin import AdminRank
from app.schemas.super_admin import SuperAdminRead, AdminLogin, SuperAdminLoginRead
from app.db.session import get_session
from fastapi.security import OAuth2PasswordRequestForm

router = APIRouter(prefix="")
service = SuperAdminService()


@router.post("/",  status_code=status.HTTP_201_CREATED)
async def create_superadmin(
        response: Response,
        name: str = Form(...),
        email: str = Form(...),
        password: str = Form(...),
        phone_number: Optional[str] = Form(None),
        rank: AdminRank = Form(AdminRank.Major),
        avatar: Optional[UploadFile] = None,
        session: AsyncSession = Depends(get_session),
):
    """Create a new SuperAdmin (multipart form with image upload)."""
    new_admin = await service.create_superadmin(session, name, email, password, phone_number, rank, avatar)
    access_token = await get_access_token(str(new_admin.id))
    refresh_token = await get_refresh_token(str(new_admin.id))
    admin_refined = SuperAdminLoginRead.model_validate(new_admin)

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        samesite="Lax",
        secure=True,
        max_age=7 * 24 * 60 * 60,
    )

    return {"admin": admin_refined, "access_token": access_token}


@router.get("/", response_model=List[SuperAdminRead])
async def list_superadmins(session: AsyncSession = Depends(get_session)):
    return await service.list_superadmins(session)


@router.get("/stats")
async def get_stats(session: AsyncSession = Depends(get_session)):
    from sqlmodel import select, func
    from app.models.user import Users
    from app.models.services import Service
    from app.models.driving import DriverProfile
    from app.models.transactions import Transaction
    from app.models.posted_job import PostedJob

    user_count_res = await session.execute(select(func.count()).select_from(Users))
    user_count = user_count_res.scalar() or 0

    services_count_res = await session.execute(select(func.count()).select_from(Service))
    services_count = services_count_res.scalar() or 0

    drivers_count_res = await session.execute(select(func.count()).select_from(DriverProfile))
    drivers_count = drivers_count_res.scalar() or 0

    tx_revenue_res = await session.execute(select(func.sum(Transaction.amount_cents)).select_from(Transaction))
    tx_revenue = tx_revenue_res.scalar() or 0

    posted_jobs_count_res = await session.execute(select(func.count()).select_from(PostedJob))
    posted_jobs_count = posted_jobs_count_res.scalar() or 0

    # Get recent users
    recent_users_res = await session.execute(select(Users).order_by(Users.created_at.desc()).limit(10))
    recent_users = recent_users_res.scalars().all()

    # Get recent services
    from sqlalchemy.orm import selectinload
    recent_services_res = await session.execute(
        select(Service).options(selectinload(Service.user)).order_by(Service.created_at.desc()).limit(10)
    )
    recent_services = recent_services_res.scalars().all()

    # Get recent posted jobs
    recent_posted_jobs_res = await session.execute(
        select(PostedJob).options(selectinload(PostedJob.user), selectinload(PostedJob.category)).order_by(PostedJob.created_at.desc()).limit(10)
    )
    recent_posted_jobs = recent_posted_jobs_res.scalars().all()

    return {
        "total_users": user_count,
        "total_services": services_count,
        "active_drivers": drivers_count,
        "total_posted_jobs": posted_jobs_count,
        "total_revenue": float(tx_revenue) / 100.0,
        "recent_users": [
            {
                "name": u.username,
                "email": u.email,
                "id": str(u.id)[:12].upper(),
                "full_id": str(u.id),
                "joined": u.created_at.strftime("%d/%m/%Y") if u.created_at else "",
                "status": u.status.value.upper() if hasattr(u.status, "value") else str(u.status).upper()
            }
            for u in recent_users
        ],
        "recent_services": [
            {
                "id": str(s.id),
                "user": u.username if (u := getattr(s, "user", None)) else "Anonymous",
                "title": s.name,
                "type": s.type.value if hasattr(s.type, "value") else str(s.type),
                "listed": s.created_at.strftime("%d/%m/%Y") if s.created_at else "",
                "status": s.status.value.upper() if hasattr(s.status, "value") else str(s.status).upper()
            }
            for s in recent_services
        ],
        "recent_posted_jobs": [
            {
                "id": str(pj.id),
                "user": u.username if (u := getattr(pj, "user", None)) else "Anonymous",
                "title": pj.title,
                "category": c.name if (c := getattr(pj, "category", None)) else "General",
                "min_price": pj.min_price_cents / 100.0,
                "max_price": pj.max_price_cents / 100.0,
                "listed": pj.created_at.strftime("%d/%m/%Y") if pj.created_at else "",
                "status": pj.status.value.upper() if hasattr(pj.status, "value") else str(pj.status).upper()
            }
            for pj in recent_posted_jobs
        ]
    }


@router.get("/{admin_id:uuid}", response_model=SuperAdminRead)
async def get_superadmin(admin_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    return await service.get_superadmin(session, admin_id)


@router.put("/{admin_id:uuid}", response_model=SuperAdminRead)
async def update_superadmin(
    admin_id: uuid.UUID,
    req: Request,
    session: AsyncSession = Depends(get_session)
):
    from app.models.admin import SuperAdmin
    from sqlmodel import select
    try:
        body = await req.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    stmt = select(SuperAdmin).where(SuperAdmin.id == admin_id)
    res = await session.execute(stmt)
    admin = res.scalar_one_or_none()
    if not admin:
        raise HTTPException(status_code=404, detail="Admin not found")

    if "name" in body:
        admin.name = body["name"]
    if "phone" in body:
        admin.phone_number = body["phone"]
    if "phone_number" in body:
        admin.phone_number = body["phone_number"]
    if "email" in body:
        admin.email = body["email"]
    if "rank" in body:
        admin.rank = body["rank"]
    if "status" in body:
        status_val = body["status"].strip().capitalize()
        if status_val == "Active":
            status_val = "Approved"
        elif status_val == "Pending":
            status_val = "Pending"
        elif status_val == "Suspended":
            status_val = "Suspended"
        elif status_val == "Rejected":
            status_val = "Rejected"
        else:
            status_val = "Approved"
        admin.status = status_val

    await session.commit()
    await session.refresh(admin)
    return admin


@router.delete("/{admin_id:uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_superadmin(admin_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    await service.delete_superadmin(session, admin_id)
    return None



@router.post("/login")
async def login(
        request: Request,
        response: Response,
        db: AsyncSession = Depends(get_session),
        form_data: OAuth2PasswordRequestForm = Depends()):
    from app.models.admin import AdminSession
    
    admin_info = AdminLogin.model_validate({"username": form_data.username, "password": form_data.password})
    admin_details = await service.admin_login(db, admin_info)

    access_token = await get_access_token(str(admin_details.id))
    refresh_token = await get_refresh_token(str(admin_details.id))
    admin_refined = SuperAdminLoginRead.model_validate(admin_details)

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        samesite="Lax",
        secure=True,
        max_age=7 * 24 * 60 * 60,
    )
    
    # Log the session
    ip_address = request.client.host if request.client else "Unknown"
    user_agent = request.headers.get("user-agent", "Unknown Device")
    
    # Use a simple heuristic for device
    device_str = user_agent
    if "Windows" in user_agent: device_str = "Windows"
    elif "Mac OS X" in user_agent or "Macintosh" in user_agent: device_str = "MacOS"
    elif "Linux" in user_agent: device_str = "Linux"
    elif "Android" in user_agent: device_str = "Android"
    elif "iPhone" in user_agent or "iPad" in user_agent: device_str = "iOS"
    else: device_str = "Unknown Device"

    new_session = AdminSession(
        admin_id=admin_details.id,
        device=device_str,
        location="Unknown",
        ip_address=ip_address
    )
    db.add(new_session)
    await db.commit()

    return {"admin": admin_refined, "access_token": access_token}


@router.get("/sessions")
async def get_sessions(
    admin: SuperAdminRead = Depends(get_current_admin),
    db: AsyncSession = Depends(get_session)
):
    from sqlmodel import select
    from app.models.admin import AdminSession
    stmt = select(AdminSession).where(AdminSession.admin_id == admin.id).order_by(AdminSession.last_activity.desc())
    res = await db.execute(stmt)
    sessions = res.scalars().all()
    return sessions

@router.get("/preferences")
async def get_preferences(admin: SuperAdminRead = Depends(get_current_admin)):
    return {
        "emailNotifs": admin.email_notifs,
        "pushNotifs": admin.push_notifs,
        "securityAlerts": admin.security_alerts
    }

from pydantic import BaseModel

class PreferencesUpdate(BaseModel):
    emailNotifs: bool
    pushNotifs: bool
    securityAlerts: bool

@router.put("/preferences")
async def update_preferences(
    prefs: PreferencesUpdate,
    admin: SuperAdminRead = Depends(get_current_admin),
    db: AsyncSession = Depends(get_session)
):
    from sqlmodel import select
    from app.models.admin import SuperAdmin
    
    stmt = select(SuperAdmin).where(SuperAdmin.id == admin.id)
    res = await db.execute(stmt)
    db_admin = res.scalar_one_or_none()
    
    if db_admin:
        db_admin.email_notifs = prefs.emailNotifs
        db_admin.push_notifs = prefs.pushNotifs
        db_admin.security_alerts = prefs.securityAlerts
        await db.commit()
        await db.refresh(db_admin)
        return {"status": "success"}
    
    raise HTTPException(status_code=404, detail="Admin not found")


class KYCSettingsUpdate(BaseModel):
    active_provider: str  # "sumsub" or "metamap"

@router.get("/kyc-settings")
async def get_admin_kyc_settings(
    db: AsyncSession = Depends(get_session)
):
    from sqlmodel import select
    from app.models.admin import AdminKYCSettings
    from app.config import settings

    stmt = select(AdminKYCSettings).where(AdminKYCSettings.id == 1)
    res = await db.execute(stmt)
    kyc_set = res.scalar_one_or_none()
    active_provider = kyc_set.active_provider if kyc_set else settings.default_kyc_provider

    return {
        "active_provider": active_provider or "sumsub",
        "updated_at": kyc_set.updated_at.isoformat() if kyc_set and kyc_set.updated_at else None,
        "updated_by_admin_id": str(kyc_set.updated_by_admin_id) if kyc_set and kyc_set.updated_by_admin_id else None
    }


@router.put("/kyc-settings")
async def update_admin_kyc_settings(
    req: KYCSettingsUpdate,
    db: AsyncSession = Depends(get_session),
    admin: SuperAdminRead = Depends(get_current_admin)
):
    from sqlmodel import select
    from app.models.admin import AdminKYCSettings
    from datetime import datetime, timezone

    provider = req.active_provider.lower().strip()
    if provider not in ["sumsub", "metamap"]:
        raise HTTPException(status_code=400, detail="Invalid provider. Must be 'sumsub' or 'metamap'")

    stmt = select(AdminKYCSettings).where(AdminKYCSettings.id == 1)
    res = await db.execute(stmt)
    kyc_set = res.scalar_one_or_none()

    if not kyc_set:
        kyc_set = AdminKYCSettings(
            id=1,
            active_provider=provider,
            updated_at=datetime.now(timezone.utc),
            updated_by_admin_id=admin.id
        )
        db.add(kyc_set)
    else:
        kyc_set.active_provider = provider
        kyc_set.updated_at = datetime.now(timezone.utc)
        kyc_set.updated_by_admin_id = admin.id
        db.add(kyc_set)

    await db.commit()
    await db.refresh(kyc_set)
    return {
        "status": "success",
        "active_provider": kyc_set.active_provider,
        "updated_at": kyc_set.updated_at.isoformat()
    }



@router.post("/services/status")
async def change_service_status(
    request: Request,
    service_id: Optional[str] = Form(None),
    status: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_session)
):
    from app.models.services import Service, ServiceStatus
    from sqlmodel import select

    if not service_id or not status:
        try:
            body = await request.json()
            service_id = service_id or body.get("service_id") or body.get("serviceId")
            status = status or body.get("status")
        except Exception:
            pass

    if not service_id or not status:
        raise HTTPException(status_code=400, detail="Missing service_id or status")

    try:
        service_uuid = uuid.UUID(service_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid service_id format")

    stmt = select(Service).where(Service.id == service_uuid)
    res = await db.execute(stmt)
    s = res.scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=404, detail="Service not found")

    if status.upper() == "DELETE":
        await db.delete(s)
        await db.commit()
        return {"message": "Service deleted successfully"}

    try:
        if status.upper() == "ACTIVE":
            s.status = ServiceStatus.approved
        elif status.upper() == "DRAFT":
            s.status = ServiceStatus.draft
        await db.commit()
        await db.refresh(s)

        try:
            from app.repositories.user_repo import get_user_by_id
            user_obj = await get_user_by_id(s.user_id, db)
            if user_obj:
                from app.services.email_notification_service import NotificationService
                NotificationService().send_service_status_mail(user_obj, s, status.lower())
        except Exception as ex:
            print(f"Failed to send service status email: {ex}")

        return {"message": "Status updated successfully", "status": s.status.value if hasattr(s.status, "value") else str(s.status)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/users/status")
async def change_user_status(
    request: Request,
    user_id: Optional[str] = Form(None),
    status: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_session)
):
    from app.models.user import Users, UserStatus
    from sqlmodel import select

    if not user_id or not status:
        try:
            body = await request.json()
            user_id = user_id or body.get("user_id") or body.get("userId")
            status = status or body.get("status")
        except Exception:
            pass

    if not user_id or not status:
        raise HTTPException(status_code=400, detail="Missing user_id or status")

    try:
        user_uuid = uuid.UUID(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user_id format")

    stmt = select(Users).where(Users.id == user_uuid)
    res = await db.execute(stmt)
    u = res.scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")

    if status.upper() == "DELETE":
        await db.delete(u)
        await db.commit()
        return {"message": "User deleted successfully"}

    try:
        if status.upper() == "ACTIVE":
            u.status = UserStatus.active
        elif status.upper() == "INACTIVE":
            u.status = UserStatus.inactive
        elif status.upper() == "BANNED":
            u.status = UserStatus.banned
        await db.commit()
        await db.refresh(u)
        return {"message": "User status updated successfully", "status": u.status.value if hasattr(u.status, "value") else str(u.status)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/notifications")
async def create_admin_notification(
    request: Request,
    db: AsyncSession = Depends(get_session)
):
    from app.models.notifications import AdminNotification, Notification, NotificationType
    from app.models.user import Users, UserStatus, KYCStatus
    from app.services.email_notification_service import NotificationService
    from app.config import settings
    from sqlmodel import select

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    title = body.get("title")
    message = body.get("message")
    recipients = body.get("recipients")
    delivery_type = body.get("type")

    if not title or not message or not recipients or not delivery_type:
        raise HTTPException(status_code=400, detail="Missing required fields")

    # Select targeted users
    stmt = select(Users)
    recip_key = str(recipients).lower()
    if "active" in recip_key:
        stmt = stmt.where(Users.status == UserStatus.active)
    elif "verified" in recip_key:
        stmt = stmt.where(
            (Users.kyc_status == KYCStatus.approved) | (Users.email_verified == True)
        )
    elif "pending" in recip_key:
        stmt = stmt.where(
            (Users.kyc_status == KYCStatus.pending) | (Users.email_verified == False)
        )
    elif "inactive" in recip_key:
        stmt = stmt.where(Users.status != UserStatus.active)

    res = await db.execute(stmt)
    target_users = res.scalars().all()

    delivery_key = str(delivery_type).lower()
    send_email = "email" in delivery_key or "both" in delivery_key
    send_push = "push" in delivery_key or "in-app" in delivery_key or "both" in delivery_key

    notifier = NotificationService()

    for u in target_users:
        if send_push:
            try:
                n = Notification(
                    user_id=u.id,
                    message=f"{title}: {message}",
                    type=NotificationType.general,
                    is_read=False
                )
                db.add(n)
            except Exception as notif_err:
                print(f"Failed to create push notification record for user {u.id}: {notif_err}")

        if send_email and getattr(u, 'email', None):
            try:
                frontend_base = getattr(settings, 'frontend_url', 'https://dgespace.com')
                context = {
                    'name': getattr(u, 'username', 'Valued User'),
                    'title': title,
                    'message': message,
                    'cta_link': f"{frontend_base}/dashboard"
                }
                notifier._render_and_dispatch('ticket_notification.html', [str(u.email)], f"[DGE Announcement] {title}", context)
            except Exception as mail_err:
                print(f"Failed to send admin email to {u.email}: {mail_err}")

    notif = AdminNotification(
        title=title,
        message=message,
        recipients=recipients,
        type=delivery_type,
        status="DELIVERED"
    )
    db.add(notif)
    await db.commit()
    await db.refresh(notif)
    return notif


@router.get("/notifications")
async def list_admin_notifications(
    db: AsyncSession = Depends(get_session)
):
    from app.models.notifications import AdminNotification
    from sqlmodel import select
    stmt = select(AdminNotification).order_by(AdminNotification.created_at.desc())
    res = await db.execute(stmt)
    notifications = res.scalars().all()
    return notifications


@router.delete("/notifications/{notification_id}")
async def delete_admin_notification(
    notification_id: str,
    db: AsyncSession = Depends(get_session)
):
    from app.models.notifications import AdminNotification
    from sqlmodel import select

    try:
        notif_uuid = uuid.UUID(notification_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid notification_id format")

    stmt = select(AdminNotification).where(AdminNotification.id == notif_uuid)
    res = await db.execute(stmt)
    n = res.scalar_one_or_none()
    if not n:
        raise HTTPException(status_code=404, detail="Notification not found")

    await db.delete(n)
    await db.commit()
    return {"message": "Notification deleted successfully"}


@router.get("/categories")
async def list_super_admin_categories(db: AsyncSession = Depends(get_session)):
    from app.models.services import ServiceCategory
    from sqlmodel import select
    stmt = select(ServiceCategory)
    res = await db.execute(stmt)
    return res.scalars().all()


@router.post("/categories")
async def create_super_admin_category(req: Request, db: AsyncSession = Depends(get_session)):
    from app.models.services import ServiceCategory
    try:
        body = await req.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    name = body.get("name")
    icon = body.get("icon")
    if not name:
        raise HTTPException(status_code=400, detail="Missing name")
    cat = ServiceCategory(name=name, icon=icon)
    db.add(cat)
    await db.commit()
    await db.refresh(cat)
    return cat


@router.put("/categories/{category_id}")
async def update_super_admin_category(category_id: str, req: Request, db: AsyncSession = Depends(get_session)):
    from app.models.services import ServiceCategory
    from sqlmodel import select
    try:
        cat_uuid = uuid.UUID(category_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid UUID")
    try:
        body = await req.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    name = body.get("name")
    icon = body.get("icon")
    if not name:
        raise HTTPException(status_code=400, detail="Missing name")
    stmt = select(ServiceCategory).where(ServiceCategory.id == cat_uuid)
    res = await db.execute(stmt)
    cat = res.scalar_one_or_none()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    cat.name = name
    cat.icon = icon
    await db.commit()
    await db.refresh(cat)
    return cat


@router.delete("/categories/{category_id}")
async def delete_super_admin_category(category_id: str, db: AsyncSession = Depends(get_session)):
    from app.models.services import ServiceCategory
    from sqlmodel import select
    try:
        cat_uuid = uuid.UUID(category_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid UUID")
    stmt = select(ServiceCategory).where(ServiceCategory.id == cat_uuid)
    res = await db.execute(stmt)
    cat = res.scalar_one_or_none()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    await db.delete(cat)
    await db.commit()
    return {"message": "Category deleted successfully"}


@router.post("/change-password")
async def super_admin_change_password(
    req: Request,
    db: AsyncSession = Depends(get_session)
):
    from app.models.user import Users
    from sqlmodel import select
    from app.core.security import get_password_hash

    try:
        body = await req.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    user_id = body.get("user_id")
    new_pass = body.get("password")

    if not user_id or not new_pass:
        raise HTTPException(status_code=400, detail="Missing user_id or password")

    try:
        user_uuid = uuid.UUID(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user_id format")

    stmt = select(Users).where(Users.id == user_uuid)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.password_hash = get_password_hash(new_pass)
    await db.commit()
    return {"message": "Password updated successfully"}


# ──────────────────────────────────────────────
#  ADMIN-FACING USER MANAGEMENT ENDPOINTS
# ──────────────────────────────────────────────

@router.get("/admin-users")
async def list_admin_users(
    search: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    limit: int = 50,
    db: AsyncSession = Depends(get_session),
):
    """Return paginated list of all platform users with service counts and KYC status."""
    from app.models.user import Users
    from app.models.services import Service
    from app.models.kyc import KYC
    from sqlmodel import select, func
    from sqlalchemy.orm import selectinload

    stmt = select(Users)
    if search:
        stmt = stmt.where(
            (Users.username.ilike(f"%{search}%")) | (Users.email.ilike(f"%{search}%"))
        )
    if status:
        from app.models.user import UserStatus
        try:
            stmt = stmt.where(Users.status == UserStatus(status.lower()))
        except Exception:
            pass

    total_res = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = total_res.scalar() or 0

    stmt = stmt.order_by(Users.created_at.desc()).offset((page - 1) * limit).limit(limit)
    result = await db.execute(stmt)
    users = result.scalars().all()

    rows = []
    for u in users:
        # service count
        svc_res = await db.execute(
            select(func.count()).select_from(Service).where(Service.user_id == u.id)
        )
        svc_count = svc_res.scalar() or 0

        # KYC status
        kyc_res = await db.execute(select(KYC).where(KYC.user_id == u.id))
        kyc = kyc_res.scalar_one_or_none()
        kyc_status = kyc.status.value.upper() if kyc and hasattr(kyc.status, "value") else (str(kyc.status).upper() if kyc else "PENDING")

        rows.append({
            "id": str(u.id),
            "name": u.username,
            "email": u.email,
            "services": svc_count,
            "joined": u.created_at.strftime("%d/%m/%Y") if u.created_at else "",
            "joined_iso": u.created_at.isoformat() if u.created_at else "",
            "status": u.status.value.upper() if hasattr(u.status, "value") else str(u.status).upper(),
            "kycStatus": kyc_status,
            "email_verified": u.email_verified,
        })

    return {"users": rows, "total": total, "page": page, "limit": limit}


@router.get("/admin-users/{user_id}")
async def get_admin_user_detail(user_id: str, db: AsyncSession = Depends(get_session)):
    """Return full profile detail for a single user (for the Overview tab)."""
    from app.models.user import Users
    from app.models.kyc import KYC
    from sqlmodel import select
    try:
        uid = uuid.UUID(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user_id")

    res = await db.execute(select(Users).where(Users.id == uid))
    u = res.scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")

    kyc_res = await db.execute(select(KYC).where(KYC.user_id == uid))
    kyc = kyc_res.scalar_one_or_none()
    kyc_status = kyc.status.value.upper() if kyc and hasattr(kyc.status, "value") else (str(kyc.status).upper() if kyc else "PENDING")

    return {
        "id": str(u.id),
        "username": u.username,
        "email": u.email,
        "status": u.status.value.upper() if hasattr(u.status, "value") else str(u.status).upper(),
        "email_verified": u.email_verified,
        "phone_verified": u.phone_verified,
        "created_at": u.created_at.isoformat() if u.created_at else None,
        "kyc_status": kyc_status,
        # KYC personal info
        "kyc_first_name": kyc.first_name if kyc else None,
        "kyc_last_name": kyc.last_name if kyc else None,
        "kyc_date_of_birth": str(kyc.date_of_birth) if kyc and kyc.date_of_birth else None,
        "kyc_nationality": kyc.nationality if kyc else None,
        "kyc_address": f"{kyc.address_line_1}, {kyc.city}, {kyc.country} {kyc.postal_code}".strip(", ") if kyc and kyc.address_line_1 else None,
        # KYC document info
        "kyc_document_type": kyc.id_document_type.value if kyc and kyc.id_document_type else None,
        "kyc_document_number": kyc.id_document_value if kyc else None,
        "kyc_document_url": kyc.id_document_s3_key if kyc else None,
        # KYC dates
        "kyc_verified_date": kyc.reviewed_at.isoformat() if kyc and kyc.reviewed_at else None,
        "kyc_uploaded_date": kyc.submitted_at.isoformat() if kyc and kyc.submitted_at else None,
        "kyc_created_at": kyc.created_at.isoformat() if kyc and kyc.created_at else None,
        "kyc_rejection_reason": kyc.rejection_reason if kyc else None,
    }


@router.get("/admin-users/{user_id}/services")
async def get_admin_user_services(user_id: str, db: AsyncSession = Depends(get_session)):
    """Return all services listed by a user."""
    from app.models.services import Service
    from sqlmodel import select
    try:
        uid = uuid.UUID(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user_id")

    res = await db.execute(
        select(Service).where(Service.user_id == uid).order_by(Service.created_at.desc())
    )
    services = res.scalars().all()
    return [
        {
            "id": str(s.id),
            "title": s.name,
            "type": s.type.value if hasattr(s.type, "value") else str(s.type),
            "price": f"₦{s.price:,.0f}",
            "date": s.created_at.strftime("%d/%m/%Y") if s.created_at else "",
            "status": s.status.value.upper() if hasattr(s.status, "value") else str(s.status).upper(),
        }
        for s in services
    ]


@router.get("/admin-users/{user_id}/transactions")
async def get_admin_user_transactions(user_id: str, db: AsyncSession = Depends(get_session)):
    """Return all transactions for a user."""
    from app.models.transactions import Transaction
    from sqlmodel import select
    try:
        uid = uuid.UUID(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user_id")

    # Transaction uses users_id (not user_id) as the FK column
    res = await db.execute(
        select(Transaction).where(Transaction.users_id == uid).order_by(Transaction.created_at.desc())
    )
    txns = res.scalars().all()
    return [
        {
            "id": str(t.id),
            "reference": t.reference,
            "type": t.type.value if hasattr(t.type, "value") else str(t.type),
            "amount": f"\u20a6{t.amount_cents / 100:,.2f}",
            "amount_raw": t.amount_cents,
            "dateTime": t.created_at.strftime("%d/%m/%Y , %I:%M%p") if t.created_at else "",
            "status": t.status.value.upper() if hasattr(t.status, "value") else str(t.status).upper(),
        }
        for t in txns
    ]


@router.get("/admin-users/{user_id}/negotiations")
async def get_admin_user_negotiations(user_id: str, db: AsyncSession = Depends(get_session)):
    """Return all negotiations involving a user."""
    from app.models.price_negotiation import PriceNegotiation  # singular, not plural
    from sqlmodel import select, or_
    try:
        uid = uuid.UUID(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user_id")

    res = await db.execute(
        select(PriceNegotiation).where(
            or_(PriceNegotiation.initiator_id == uid, PriceNegotiation.receiver_id == uid)
        ).order_by(PriceNegotiation.created_at.desc())
    )
    negs = res.scalars().all()
    rows = []
    for n in negs:
        rows.append({
            "id": str(n.id),
            "title": n.message or "Negotiation",  # field is 'message', not 'note'
            "negotiator": str(n.initiator_id)[:8],
            "servicePrice": "\u20a6" + f"{n.proposed_price_cents / 100:,.0f}",  # no original_price; use proposed
            "negotiationPrice": "\u20a6" + f"{n.proposed_price_cents / 100:,.0f}",
            "date": n.created_at.strftime("%d/%m/%Y") if n.created_at else "",
            "status": n.status.value.upper() if hasattr(n.status, "value") else str(n.status).upper(),
        })
    return rows


@router.get("/admin-users/{user_id}/escrows")
async def get_admin_user_escrows(user_id: str, db: AsyncSession = Depends(get_session)):
    """Return all escrows involving a user via their wallets."""
    from app.models.escrow import Escrow
    from app.models.wallet import Wallet
    from app.models.user import Users
    from app.models.price_negotiation import PriceNegotiation
    from app.models.services import Service
    from app.models.posted_job import PostedJob
    from sqlmodel import select, or_
    from sqlalchemy.orm import aliased
    try:
        uid = uuid.UUID(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user_id")

    wallet_res = await db.execute(select(Wallet).where(Wallet.user_id == uid))
    wallets = wallet_res.scalars().all()
    wallet_ids = [w.id for w in wallets]

    if not wallet_ids:
        return []

    PayerWallet = aliased(Wallet)
    PayerUser = aliased(Users)
    PayeeWallet = aliased(Wallet)
    PayeeUser = aliased(Users)

    res = await db.execute(
        select(Escrow, PriceNegotiation, Service, PostedJob, PayerUser, PayeeUser)
        .outerjoin(PriceNegotiation, Escrow.payment_negotiation_id == PriceNegotiation.id)
        .outerjoin(Service, PriceNegotiation.service_id == Service.id)
        .outerjoin(PostedJob, PriceNegotiation.posted_job_id == PostedJob.id)
        .outerjoin(PayerWallet, Escrow.payer_wallet_id == PayerWallet.id)
        .outerjoin(PayerUser, PayerWallet.user_id == PayerUser.id)
        .outerjoin(PayeeWallet, Escrow.payee_wallet_id == PayeeWallet.id)
        .outerjoin(PayeeUser, PayeeWallet.user_id == PayeeUser.id)
        .where(
            or_(Escrow.payer_wallet_id.in_(wallet_ids), Escrow.payee_wallet_id.in_(wallet_ids))
        ).order_by(Escrow.created_at.desc())
    )
    rows = res.all()

    items = []
    for e, neg, svc, p_job, payer, payee in rows:
        title = svc.name if svc else (p_job.title if p_job else f"Escrow #{str(e.id)[:8].upper()}")
        is_payer = e.payer_wallet_id in wallet_ids
        counterparty = (payee.username if payee else "Payee") if is_payer else (payer.username if payer else "Payer")
        items.append({
            "id": str(e.id),
            "title": title,
            "counterparty": counterparty,
            "amount": f"\u20a6{e.amount_cents / 100:,.2f}",
            "date": e.created_at.strftime("%d/%m/%Y") if e.created_at else "",
            "status": e.status.value.upper() if hasattr(e.status, "value") else str(e.status).upper(),
        })
    return items


@router.get("/admin-users/{user_id}/reviews")
async def get_admin_user_reviews(user_id: str, db: AsyncSession = Depends(get_session)):
    """Return all reviews on a user's portfolio."""
    from app.models.portfolio import Review, UserPortfolio  # Review is in portfolio.py
    from app.models.user import Users
    from sqlmodel import select
    try:
        uid = uuid.UUID(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user_id")

    # Review links to portfolio, not directly to user. Find portfolio first.
    portfolio_res = await db.execute(select(UserPortfolio).where(UserPortfolio.user_id == uid))
    portfolio = portfolio_res.scalar_one_or_none()
    if not portfolio:
        return []

    res = await db.execute(
        select(Review).where(Review.portfolio_id == portfolio.id).order_by(Review.created_at.desc())
    )
    reviews = res.scalars().all()
    rows = []
    for r in reviews:
        # Review.user_id is the reviewer
        reviewer_name = str(r.user_id)[:8]
        ures = await db.execute(select(Users).where(Users.id == r.user_id))
        reviewer = ures.scalar_one_or_none()
        if reviewer:
            reviewer_name = reviewer.username
        rows.append({
            "id": str(r.id),
            "person": reviewer_name,
            "rating": r.rating,
            "message": r.comment or "",
            "date": r.created_at.strftime("%d/%m/%Y") if r.created_at else "",
        })
    return rows


@router.get("/admin-users/{user_id}/wallets")
async def get_admin_user_wallets(user_id: str, db: AsyncSession = Depends(get_session)):
    """Return wallet balances for a user."""
    from app.models.wallet import Wallet, WalletType
    from sqlmodel import select
    try:
        uid = uuid.UUID(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user_id")

    res = await db.execute(select(Wallet).where(Wallet.user_id == uid))
    wallets = list(res.scalars().all())

    # Check/auto-create deposit wallet
    has_deposit = any(w.wallet_type == WalletType.deposit for w in wallets)
    if not has_deposit:
        dep_wallet = Wallet(user_id=uid, wallet_type=WalletType.deposit, balance_cents=0, currency="NGN")
        db.add(dep_wallet)
        await db.commit()
        wallets.append(dep_wallet)

    # Check/auto-create earnings wallet
    has_earnings = any(w.wallet_type == WalletType.earnings for w in wallets)
    if not has_earnings:
        earn_wallet = Wallet(user_id=uid, wallet_type=WalletType.earnings, balance_cents=0, currency="NGN")
        db.add(earn_wallet)
        await db.commit()
        wallets.append(earn_wallet)

    return [
        {
            "id": str(w.id),
            "type": w.wallet_type.value if hasattr(w.wallet_type, "value") else str(w.wallet_type),
            "balance": w.balance_cents,
        }
        for w in wallets
    ]


@router.post("/admin-users/{user_id}/status")
async def update_admin_user_status(user_id: str, req: Request, db: AsyncSession = Depends(get_session)):
    """Suspend, activate or ban a platform user."""
    from app.models.user import Users, UserStatus
    from sqlmodel import select
    try:
        uid = uuid.UUID(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user_id")
    try:
        body = await req.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    action = body.get("status", "").lower()
    res = await db.execute(select(Users).where(Users.id == uid))
    u = res.scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")

    status_map = {"active": UserStatus.active, "inactive": UserStatus.inactive, "banned": UserStatus.banned}
    if action not in status_map:
        raise HTTPException(status_code=400, detail=f"Invalid status. Use: {list(status_map.keys())}")

    u.status = status_map[action]
    await db.commit()
    await db.refresh(u)
    return {"message": f"User status updated to {action}", "status": action}


# ──────────────────────────────────────────────
#  ADMIN-FACING DRIVER MANAGEMENT ENDPOINTS
# ──────────────────────────────────────────────

@router.get("/admin-drivers")
async def list_admin_drivers(
    search: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    limit: int = 50,
    db: AsyncSession = Depends(get_session),
):
    """Return paginated list of all rides (drivers page table)."""
    from app.models.driving import Ride, DriverProfile
    from app.models.user import Users
    from sqlmodel import select, func, or_
    
    stmt = select(Ride, DriverProfile, Users).join(DriverProfile, Ride.driver_id == DriverProfile.id).join(Users, DriverProfile.user_id == Users.id)
    
    if search:
        stmt = stmt.where(
            or_(
                Users.username.ilike(f"%{search}%"),
                Ride.start_location.ilike(f"%{search}%"),
                Ride.destination.ilike(f"%{search}%")
            )
        )
    
    if status:
        from app.models.driving import RideStatus
        try:
            stmt = stmt.where(Ride.status == RideStatus(status.lower()))
        except Exception:
            pass

    total_res = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = total_res.scalar() or 0

    stmt = stmt.order_by(Ride.start_time.desc()).offset((page - 1) * limit).limit(limit)
    result = await db.execute(stmt)
    rows = result.all()

    items = []
    for ride, profile, user in rows:
        items.append({
            "id": str(ride.id),
            "driver_id": str(profile.id),
            "name": user.username,
            "passenger": user.username, 
            "destination": ride.destination,
            "servicePrice": f"\u20a6{ride.earnings:,.0f}",
            "negotiationPrice": f"\u20a6{ride.earnings:,.0f}",
            "time": ride.start_time.strftime("%d/%m/%Y - %I:%M %p") if ride.start_time else "",
            "status": ride.status.value.upper()
        })

    # Summary counts
    active_count = (await db.execute(select(func.count()).select_from(Ride).where(Ride.status == "started"))).scalar() or 0
    completed_count = (await db.execute(select(func.count()).select_from(Ride).where(Ride.status == "completed"))).scalar() or 0
    cancelled_count = (await db.execute(select(func.count()).select_from(Ride).where(Ride.status == "cancelled"))).scalar() or 0

    return {
        "rides": items, 
        "total": total, 
        "page": page, 
        "limit": limit,
        "summary": {
            "active": active_count,
            "completed": completed_count,
            "cancelled": cancelled_count
        }
    }

@router.get("/admin-drivers/licenses")
async def list_admin_driver_licenses(
    status: Optional[str] = "pending",
    page: int = 1,
    limit: int = 50,
    db: AsyncSession = Depends(get_session),
):
    """List all driver license applications."""
    from app.models.driving import DriverProfile
    from app.models.user import Users
    from sqlmodel import select, func, or_
    
    base_filter = or_(DriverProfile.license_number != None, DriverProfile.license_picture_url != None)
    stmt = select(DriverProfile, Users).join(Users, DriverProfile.user_id == Users.id).where(base_filter)
    
    if status and status.lower() != "all":
        stmt = stmt.where(func.lower(DriverProfile.license_status) == status.lower())
        
    total_res = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = total_res.scalar() or 0
    
    stmt = stmt.order_by(DriverProfile.updated_at.desc()).offset((page - 1) * limit).limit(limit)
    res = await db.execute(stmt)
    rows = res.all()
    
    items = []
    for profile, user in rows:
        items.append({
            "id": str(profile.id),
            "user_id": str(user.id),
            "name": f"{getattr(user, 'first_name', '')} {getattr(user, 'last_name', '')}".strip() or user.username,
            "email": user.email,
            "license_number": profile.license_number or "N/A",
            "license_picture_url": profile.license_picture_url,
            "license_status": (profile.license_status or "unverified").lower(),
            "submitted_at": profile.updated_at.strftime("%d/%m/%Y") if profile.updated_at else "—",
        })
        
    pending_count = (await db.execute(select(func.count()).select_from(DriverProfile).where(base_filter).where(func.lower(DriverProfile.license_status) == "pending"))).scalar() or 0
    verified_count = (await db.execute(select(func.count()).select_from(DriverProfile).where(base_filter).where(func.lower(DriverProfile.license_status) == "verified"))).scalar() or 0
    rejected_count = (await db.execute(select(func.count()).select_from(DriverProfile).where(base_filter).where(func.lower(DriverProfile.license_status) == "rejected"))).scalar() or 0
    
    return {
        "items": items,
        "total": total,
        "summary": {
            "pending": pending_count,
            "verified": verified_count,
            "rejected": rejected_count
        }
    }


@router.get("/admin-drivers/licenses/{driver_id}")
async def get_admin_driver_license_detail(driver_id: str, db: AsyncSession = Depends(get_session)):
    """Get details of a single driver license application."""
    from app.models.driving import DriverProfile
    from app.models.user import Users
    from sqlmodel import select
    
    try:
        did = uuid.UUID(driver_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid driver_id")
        
    stmt = select(DriverProfile, Users).join(Users, DriverProfile.user_id == Users.id).where(DriverProfile.id == did)
    res = await db.execute(stmt)
    result = res.all()
    if not result:
        raise HTTPException(status_code=404, detail="Driver profile not found")
        
    profile, user = result[0]
    
    return {
        "id": str(profile.id),
        "user_id": str(user.id),
        "name": f"{getattr(user, 'first_name', '')} {getattr(user, 'last_name', '')}".strip() or user.username,
        "email": user.email,
        "license_number": profile.license_number,
        "license_picture_url": profile.license_picture_url,
        "car_picture_url": profile.car_picture_url,
        "car_name": profile.car_name,
        "car_model": profile.car_model,
        "plate_number": profile.plate_number,
        "vehicle_type": profile.vehicle_type,
        "license_status": (profile.license_status or "unverified").lower(),
        "license_rejection_reason": profile.license_rejection_reason,
        "submitted_at": profile.updated_at.isoformat() if profile.updated_at else None,
        "personal_info": {
            "phone": getattr(user, "phone", "—"),
            "car_name": profile.car_name,
            "car_model": profile.car_model,
            "plate_number": profile.plate_number,
            "vehicle_type": profile.vehicle_type,
        }
    }


@router.post("/admin-drivers/licenses/{driver_id}/review")
async def review_admin_driver_license(driver_id: str, req: Request, db: AsyncSession = Depends(get_session)):
    """Approve or reject a driver license application."""
    from app.models.driving import DriverProfile, DriverStatus
    from app.models.user import Users
    from sqlmodel import select
    
    try:
        did = uuid.UUID(driver_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid driver_id")
        
    body = await req.json()
    action = body.get("action", "").lower()
    reason = body.get("reason") or body.get("rejection_reason", "")
    
    stmt = select(DriverProfile, Users).join(Users, DriverProfile.user_id == Users.id).where(DriverProfile.id == did)
    res = await db.execute(stmt)
    result = res.all()
    if not result:
        raise HTTPException(status_code=404, detail="Driver profile not found")
        
    profile, user = result[0]
        
    if action == "approve":
        profile.license_status = "verified"
        profile.status = DriverStatus.ACTIVE
        profile.license_rejection_reason = None
    elif action == "reject":
        profile.license_status = "rejected"
        profile.status = DriverStatus.PENDING
        profile.license_rejection_reason = reason
    else:
        raise HTTPException(status_code=400, detail="Invalid action. Use 'approve' or 'reject'")
        
    db.add(profile)
    await db.commit()

    # Create In-App Notification
    try:
        from datetime import datetime, timezone
        from app.models.notifications import Notification, NotificationType
        notif_msg = "Your Driver License verification application has been approved! 🎉" if action == "approve" else f"Your Driver License verification application was rejected. Reason: {reason or 'Not specified'}"
        in_app_notif = Notification(
            user_id=profile.user_id,
            type=NotificationType.general,
            message=notif_msg,
            metadataInfo={"status": profile.license_status, "type": "driver_license"},
            is_read=False,
            created_at=datetime.now(timezone.utc)
        )
        db.add(in_app_notif)
        await db.commit()
    except Exception as ex:
        print(f"Failed to create in-app notification for driver license: {ex}")

    # Send Email Notification
    try:
        from app.services.email_notification_service import NotificationService
        notif_svc = NotificationService()
        notif_svc.send_driver_license_status_mail(user, profile.license_status, profile.license_rejection_reason)
    except Exception as ex:
        print(f"Failed to send driver license status email: {ex}")

    return {"message": f"Driver license {action}d successfully", "status": profile.license_status.lower()}


@router.get("/admin-drivers/{driver_id}")
async def get_admin_driver_detail(driver_id: str, db: AsyncSession = Depends(get_session)):
    """Return driver profile detail."""
    from app.models.driving import DriverProfile
    from app.models.user import Users
    from app.models.kyc import KYC
    from sqlmodel import select
    
    try:
        did = uuid.UUID(driver_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid driver_id")
        
    stmt = select(DriverProfile, Users).join(Users, DriverProfile.user_id == Users.id).where(DriverProfile.id == did)
    res = await db.execute(stmt)
    result = res.all()
    if not result:
        raise HTTPException(status_code=404, detail="Driver not found")
    
    profile, user = result[0]
    
    kyc_res = await db.execute(select(KYC).where(KYC.user_id == user.id))
    kyc = kyc_res.scalar_one_or_none()
    kyc_status = kyc.status.value.upper() if kyc and hasattr(kyc.status, "value") else (str(kyc.status).upper() if kyc else "PENDING")

    return {
        "id": str(profile.id),
        "user_id": str(user.id),
        "name": user.username,
        "email": user.email,
        "phone": getattr(user, "phone", "\u2014"),
        "car_name": profile.car_name,
        "car_model": profile.car_model,
        "plate_number": profile.plate_number,
        "successful_rides": profile.successful_rides,
        "total_rides": profile.total_rides,
        "failed_rides": profile.failed_rides,
        "rank": profile.rank.value.upper(),
        "status": profile.status.value.upper(),
        "created_at": profile.created_at.isoformat() if profile.created_at else None,
        "kyc_status": kyc_status,
        "email_verified": user.email_verified,
    }

@router.get("/admin-drivers/{driver_id}/rides")
async def get_admin_driver_rides(driver_id: str, status: Optional[str] = None, db: AsyncSession = Depends(get_session)):
    from app.models.driving import Ride
    from sqlmodel import select
    
    try:
        did = uuid.UUID(driver_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid driver_id")
        
    stmt = select(Ride).where(Ride.driver_id == did)
    if status:
        from app.models.driving import RideStatus
        try:
            stmt = stmt.where(Ride.status == RideStatus(status.lower()))
        except Exception:
            pass
            
    stmt = stmt.order_by(Ride.start_time.desc())
    res = await db.execute(stmt)
    rides = res.scalars().all()
    
    return [
        {
            "id": str(r.id),
            "start_location": r.start_location,
            "destination": r.destination,
            "status": r.status.value.upper(),
            "earnings": r.earnings,
            "start_time": r.start_time.isoformat() if r.start_time else None,
            "end_time": r.end_time.isoformat() if r.end_time else None,
        }
        for r in rides
    ]

@router.post("/admin-drivers/{driver_id}/status")
async def update_admin_driver_status(driver_id: str, req: Request, db: AsyncSession = Depends(get_session)):
    from app.models.driving import DriverProfile, DriverStatus
    from sqlmodel import select
    
    try:
        did = uuid.UUID(driver_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid driver_id")
        
    body = await req.json()
    action = body.get("status", "").lower()
    
    res = await db.execute(select(DriverProfile).where(DriverProfile.id == did))
    profile = res.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Driver not found")
        
    status_map = {
        "active": DriverStatus.ACTIVE,
        "suspended": DriverStatus.SUSPENDED,
        "banned": DriverStatus.BANNED,
        "pending": DriverStatus.PENDING
    }
    
    if action not in status_map:
        raise HTTPException(status_code=400, detail=f"Invalid status. Use: {list(status_map.keys())}")
        
    profile.status = status_map[action]
    await db.commit()
    return {"message": f"Driver status updated to {action}", "status": action}


# ──────────────────────────────────────────────
#  ADMIN-FACING KYC MANAGEMENT ENDPOINTS
# ──────────────────────────────────────────────

@router.get("/admin-kyc")
async def list_admin_kyc(
    status: Optional[str] = "pending",
    page: int = 1,
    limit: int = 50,
    db: AsyncSession = Depends(get_session),
):
    """List all KYC submissions."""
    from app.models.kyc import KYC, KYCStatus
    from app.models.user import Users
    from sqlmodel import select, func
    
    stmt = select(KYC, Users).join(Users, KYC.user_id == Users.id)
    
    if status and status.lower() != "all":
        try:
            stmt = stmt.where(KYC.status == KYCStatus(status.lower()))
        except Exception:
            pass
            
    total_res = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = total_res.scalar() or 0
    
    stmt = stmt.order_by(KYC.submitted_at.desc()).offset((page - 1) * limit).limit(limit)
    res = await db.execute(stmt)
    rows = res.all()
    
    items = []
    for kyc, user in rows:
        items.append({
            "id": str(kyc.user_id),
            "user_id": str(user.id),
            "name": f"{getattr(user, 'first_name', '')} {getattr(user, 'last_name', '')}".strip() or user.username,
            "email": user.email,
            "id_type": kyc.id_document_type.value if hasattr(kyc.id_document_type, "value") else str(kyc.id_document_type),
            "id_value": kyc.id_document_value,
            "submitted_at": kyc.submitted_at.strftime("%d/%m/%Y") if kyc.submitted_at else "\u2014",
            "status": kyc.status.value.upper() if hasattr(kyc.status, "value") else str(kyc.status).upper(),
        })
        
    # Stats
    pending_count = (await db.execute(select(func.count()).select_from(KYC).where(KYC.status == KYCStatus.pending))).scalar() or 0
    verified_count = (await db.execute(select(func.count()).select_from(KYC).where(KYC.status == KYCStatus.verified))).scalar() or 0
    rejected_count = (await db.execute(select(func.count()).select_from(KYC).where(KYC.status == KYCStatus.rejected))).scalar() or 0
    
    return {
        "items": items,
        "total": total,
        "summary": {
            "pending": pending_count,
            "verified": verified_count,
            "rejected": rejected_count
        }
    }

@router.get("/admin-kyc/{user_id}")
async def get_admin_kyc_detail(user_id: str, db: AsyncSession = Depends(get_session)):
    from app.models.kyc import KYC
    from app.models.user import Users
    from sqlmodel import select
    
    try:
        uid = uuid.UUID(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user_id")
        
    stmt = select(KYC, Users).join(Users, KYC.user_id == Users.id).where(KYC.user_id == uid)
    res = await db.execute(stmt)
    result = res.all()
    if not result:
        raise HTTPException(status_code=404, detail="KYC not found for this user")
        
    kyc, user = result[0]
    
    return {
        "id": str(kyc.user_id),
        "user_id": str(user.id),
        "name": f"{getattr(user, 'first_name', '')} {getattr(user, 'last_name', '')}".strip() or user.username,
        "email": user.email,
        "id_type": kyc.id_document_type.value if hasattr(kyc.id_document_type, "value") else str(kyc.id_document_type),
        "id_value": kyc.id_document_value,
        "id_document_url": kyc.id_document_s3_key,
        "submitted_at": kyc.submitted_at.isoformat() if kyc.submitted_at else None,
        "reviewed_at": kyc.reviewed_at.isoformat() if kyc.reviewed_at else None,
        "status": kyc.status.value.upper() if hasattr(kyc.status, "value") else str(kyc.status).upper(),
        "rejection_reason": kyc.rejection_reason,
        "personal_info": {
            "nationality": getattr(user, "nationality", "\u2014"),
            "address": getattr(user, "address", "\u2014"),
            "dob": getattr(user, "dob", "\u2014"),
        }
    }

@router.post("/admin-kyc/{user_id}/review")
async def review_admin_kyc(user_id: str, req: Request, db: AsyncSession = Depends(get_session)):
    from app.models.kyc import KYC, KYCStatus
    from datetime import datetime, timezone
    from sqlmodel import select
    
    try:
        uid = uuid.UUID(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user_id")
        
    body = await req.json()
    action = body.get("action", "").lower() # approve or reject
    reason = body.get("reason", "")
    
    res = await db.execute(select(KYC).where(KYC.user_id == uid))
    kyc = res.scalar_one_or_none()
    if not kyc:
        from app.models.user import Users
        user_res = await db.execute(select(Users).where(Users.id == uid))
        user_obj = user_res.scalar_one_or_none()
        if not user_obj:
            raise HTTPException(status_code=404, detail="User not found")
        
        kyc = KYC(
            user_id=uid,
            status=KYCStatus.unverified,
            submitted_at=datetime.now(timezone.utc)
        )
        db.add(kyc)
        
    if action == "approve":
        kyc.status = KYCStatus.verified
    elif action == "reject":
        kyc.status = KYCStatus.rejected
        kyc.rejection_reason = reason
    else:
        raise HTTPException(status_code=400, detail="Invalid action. Use 'approve' or 'reject'")
        
    kyc.reviewed_at = datetime.now(timezone.utc)
    # Create In-App Notification
    try:
        from app.models.notifications import Notification, NotificationType
        notif_msg = "Your KYC verification has been approved! 🎉" if action == "approve" else f"Your KYC verification was rejected. Reason: {reason or 'Not specified'}"
        in_app_notif = Notification(
            user_id=uid,
            type=NotificationType.general,
            message=notif_msg,
            metadataInfo={"status": kyc.status.value if hasattr(kyc.status, "value") else str(kyc.status), "type": "kyc"},
            is_read=False,
            created_at=datetime.now(timezone.utc)
        )
        db.add(in_app_notif)
        await db.commit()
    except Exception as ex:
        print(f"Failed to create in-app notification for KYC: {ex}")

    # Send Email Notification
    try:
        from app.repositories.user_repo import get_user_by_id
        user_obj = await get_user_by_id(uid, db)
        if user_obj:
            from app.services.email_notification_service import NotificationService
            NotificationService().send_kyc_status_mail(user_obj, kyc.status.value if hasattr(kyc.status, "value") else str(kyc.status), reason if action == "reject" else None)
    except Exception as ex:
        print(f"Failed to send KYC status email: {ex}")

    return {"message": f"KYC {action}d successfully", "status": kyc.status.value.upper()}




# ──────────────────────────────────────────────
#  ADMIN-FACING NEGOTIATION MANAGEMENT ENDPOINTS
# ──────────────────────────────────────────────

@router.get("/admin-negotiations")
async def list_admin_negotiations(
    status: Optional[str] = "pending",
    page: int = 1,
    limit: int = 50,
    db: AsyncSession = Depends(get_session),
):
    """List all price negotiations."""
    from app.models.price_negotiation import PriceNegotiation, NegotiationStatus
    from app.models.user import Users
    from app.models.services import Service
    from sqlmodel import select, func
    from sqlalchemy.orm import aliased
    
    Initiator = aliased(Users)
    Receiver = aliased(Users)
    
    stmt = select(PriceNegotiation, Initiator, Receiver, Service)\
        .join(Initiator, PriceNegotiation.initiator_id == Initiator.id)\
        .join(Receiver, PriceNegotiation.receiver_id == Receiver.id)\
        .join(Service, PriceNegotiation.service_id == Service.id)
    
    if status and status.lower() != "all":
        try:
            stmt = stmt.where(PriceNegotiation.status == NegotiationStatus(status.lower()))
        except Exception:
            pass
            
    total_res = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = total_res.scalar() or 0
    
    stmt = stmt.order_by(PriceNegotiation.created_at.desc()).offset((page - 1) * limit).limit(limit)
    res = await db.execute(stmt)
    rows = res.all()
    
    items = []
    for neg, init, recv, svc in rows:
        items.append({
            "id": str(neg.id),
            "service_name": svc.name,
            "initiator_name": init.username,
            "receiver_name": recv.username,
            "proposed_price": f"\u20a6{neg.proposed_price_cents / 100:,.2f}",
            "original_price": f"\u20a6{svc.price:,.2f}" if svc.price else "\u2014",
            "message": neg.message,
            "status": neg.status.value.upper(),
            "created_at": neg.created_at.strftime("%d/%m/%Y - %I:%M %p") if neg.created_at else "\u2014",
        })
        
    # Stats
    pending_count = (await db.execute(select(func.count()).select_from(PriceNegotiation).where(PriceNegotiation.status == NegotiationStatus.pending))).scalar() or 0
    accepted_count = (await db.execute(select(func.count()).select_from(PriceNegotiation).where(PriceNegotiation.status == NegotiationStatus.accepted))).scalar() or 0
    rejected_count = (await db.execute(select(func.count()).select_from(PriceNegotiation).where(PriceNegotiation.status == NegotiationStatus.rejected))).scalar() or 0
    
    return {
        "items": items,
        "total": total,
        "summary": {
            "pending": pending_count,
            "accepted": accepted_count,
            "rejected": rejected_count
        }
    }

@router.get("/admin-negotiations/{negotiation_id}")
async def get_negotiation_detail(
    negotiation_id: str,
    db: AsyncSession = Depends(get_session),
):
    """Get detailed information about a price negotiation."""
    from app.models.price_negotiation import PriceNegotiation
    from app.models.user import Users
    from app.models.services import Service
    from sqlmodel import select
    from sqlalchemy.orm import aliased
    
    try:
        nid = uuid.UUID(negotiation_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid negotiation_id")
        
    Initiator = aliased(Users)
    Receiver = aliased(Users)
    
    stmt = select(PriceNegotiation, Initiator, Receiver, Service)\
        .join(Initiator, PriceNegotiation.initiator_id == Initiator.id)\
        .join(Receiver, PriceNegotiation.receiver_id == Receiver.id)\
        .join(Service, PriceNegotiation.service_id == Service.id)\
        .where(PriceNegotiation.id == nid)
        
    res = await db.execute(stmt)
    result = res.all()
    if not result:
        raise HTTPException(status_code=404, detail="Negotiation not found")
        
    neg, init, recv, svc = result[0]
    
    return {
        "id": str(neg.id),
        "service": {
            "id": str(svc.id),
            "name": svc.name,
            "original_price": f"\u20a6{svc.price:,.2f}"
        },
        "initiator": {
            "id": str(init.id),
            "username": init.username,
            "email": init.email
        },
        "receiver": {
            "id": str(recv.id),
            "username": recv.username,
            "email": recv.email
        },
        "proposed_price": f"\u20a6{neg.proposed_price_cents / 100:,.2f}",
        "message": neg.message,
        "status": neg.status.value.upper(),
        "created_at": neg.created_at.isoformat() if neg.created_at else None,
        "updated_at": neg.updated_at.isoformat() if neg.updated_at else None,
    }

@router.post("/admin-negotiations/{negotiation_id}/status")
async def update_negotiation_status(
    negotiation_id: str,
    req: Request,
    db: AsyncSession = Depends(get_session),
):
    """Update negotiation status (admin override)."""
    from app.models.price_negotiation import PriceNegotiation, NegotiationStatus
    from sqlmodel import select
    
    try:
        nid = uuid.UUID(negotiation_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid negotiation_id")
        
    body = await req.json()
    action = body.get("action", "").lower() # accept or reject
    
    res = await db.execute(select(PriceNegotiation).where(PriceNegotiation.id == nid))
    neg = res.scalar_one_or_none()
    if not neg:
        raise HTTPException(status_code=404, detail="Negotiation not found")
        
    if action == "accept":
        neg.status = NegotiationStatus.accepted
    elif action == "reject":
        neg.status = NegotiationStatus.rejected
    else:
        neg.status = NegotiationStatus.rejected if action == "reject" else NegotiationStatus.accepted
    await db.commit()
    return {"message": f"Negotiation {action}ed successfully", "status": neg.status.value.upper()}
    
@router.delete("/admin-negotiations/{negotiation_id}")
async def delete_negotiation(
    negotiation_id: str,
    db: AsyncSession = Depends(get_session),
):
    """Delete a price negotiation."""
    from app.models.price_negotiation import PriceNegotiation
    
    try:
        nid = uuid.UUID(negotiation_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid negotiation_id")
        
    neg = await db.get(PriceNegotiation, nid)
    if not neg:
        raise HTTPException(status_code=404, detail="Negotiation not found")
        
    await db.delete(neg)
    await db.commit()
    return {"message": "Negotiation deleted successfully"}


# ──────────────────────────────────────────────
#  ADMIN-FACING ESCROW & TRANSACTION ENDPOINTS
# ──────────────────────────────────────────────

@router.get("/admin-escrows")
async def list_admin_escrows(
    status: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    limit: int = 50,
    db: AsyncSession = Depends(get_session),
):
    """List all escrows."""
    from app.models.escrow import Escrow, EscrowStatus
    from app.models.price_negotiation import PriceNegotiation
    from app.models.services import Service
    from app.models.posted_job import PostedJob
    from app.models.user import Users
    from app.models.wallet import Wallet
    from sqlmodel import select, func
    from sqlalchemy.orm import aliased
    
    PayerWallet = aliased(Wallet)
    PayerUser = aliased(Users)
    PayeeWallet = aliased(Wallet)
    PayeeUser = aliased(Users)
    
    stmt = select(Escrow, PriceNegotiation, Service, PostedJob, PayerUser, PayeeUser)\
        .outerjoin(PriceNegotiation, Escrow.payment_negotiation_id == PriceNegotiation.id)\
        .outerjoin(Service, PriceNegotiation.service_id == Service.id)\
        .outerjoin(PostedJob, PriceNegotiation.posted_job_id == PostedJob.id)\
        .outerjoin(PayerWallet, Escrow.payer_wallet_id == PayerWallet.id)\
        .outerjoin(PayerUser, PayerWallet.user_id == PayerUser.id)\
        .outerjoin(PayeeWallet, Escrow.payee_wallet_id == PayeeWallet.id)\
        .outerjoin(PayeeUser, PayeeWallet.user_id == PayeeUser.id)

    count_stmt = select(func.count(Escrow.id)).select_from(Escrow)\
        .outerjoin(PriceNegotiation, Escrow.payment_negotiation_id == PriceNegotiation.id)\
        .outerjoin(Service, PriceNegotiation.service_id == Service.id)\
        .outerjoin(PostedJob, PriceNegotiation.posted_job_id == PostedJob.id)\
        .outerjoin(PayerWallet, Escrow.payer_wallet_id == PayerWallet.id)\
        .outerjoin(PayerUser, PayerWallet.user_id == PayerUser.id)\
        .outerjoin(PayeeWallet, Escrow.payee_wallet_id == PayeeWallet.id)\
        .outerjoin(PayeeUser, PayeeWallet.user_id == PayeeUser.id)
        
    if status and status.lower() != "all":
        try:
            target_status = EscrowStatus(status.lower())
            stmt = stmt.where(Escrow.status == target_status)
            count_stmt = count_stmt.where(Escrow.status == target_status)
        except Exception:
            pass

    if search:
        search_term = f"%{search.strip()}%"
        search_filter = (
            PayerUser.username.ilike(search_term) |
            PayeeUser.username.ilike(search_term) |
            Service.name.ilike(search_term) |
            PostedJob.title.ilike(search_term)
        )
        try:
            search_uuid = uuid.UUID(search.strip())
            search_filter = search_filter | (Escrow.id == search_uuid)
        except Exception:
            pass

        stmt = stmt.where(search_filter)
        count_stmt = count_stmt.where(search_filter)
            
    total_res = await db.execute(count_stmt)
    total = total_res.scalar() or 0
    
    stmt = stmt.order_by(Escrow.created_at.desc()).offset((page - 1) * limit).limit(limit)
    res = await db.execute(stmt)
    rows = res.all()
    
    from app.services.fee_service import fee_service
    from app.models.admin import PlatformRevenueLog

    fee_config = await fee_service.get_fee_config(db)

    items = []
    for esc, neg, svc, p_job, payer, payee in rows:
        service_name = svc.name if svc else (p_job.title if p_job else "Escrow Service")

        # Fee & Net released calculation
        fee_log_stmt = select(PlatformRevenueLog).where(
            PlatformRevenueLog.reference == str(esc.id),
            PlatformRevenueLog.event_type == "escrow_release"
        )
        fee_log_res = await db.execute(fee_log_stmt)
        fee_log = fee_log_res.scalar_one_or_none()

        if fee_log:
            fee_cents = fee_log.fee_amount_cents
        elif fee_config.escrow_release_fee_enabled:
            fee_cents = fee_service.calculate_fee(
                esc.amount_cents,
                fee_config.escrow_release_fee_type,
                fee_config.escrow_release_fee_value
            )
        else:
            fee_cents = 0

        net_released_cents = max(0, esc.amount_cents - fee_cents)

        items.append({
            "id": str(esc.id),
            "service_name": service_name,
            "payer_name": payer.username if payer else "Payer",
            "payee_name": payee.username if payee else "Payee",
            "amount": f"₦{esc.amount_cents / 100:,.2f}",
            "fee_amount": f"₦{fee_cents / 100:,.2f}",
            "released_amount": f"₦{net_released_cents / 100:,.2f}",
            "fee_cents": fee_cents,
            "net_released_cents": net_released_cents,
            "status": esc.status.value.upper() if hasattr(esc.status, "value") else str(esc.status).upper(),
            "created_at": esc.created_at.strftime("%d/%m/%Y") if esc.created_at else "—",
        })
        
    # Stats
    held_count = (await db.execute(select(func.count()).select_from(Escrow).where(Escrow.status == EscrowStatus.held))).scalar() or 0
    released_count = (await db.execute(select(func.count()).select_from(Escrow).where(Escrow.status == EscrowStatus.released))).scalar() or 0
    refunded_count = (await db.execute(select(func.count()).select_from(Escrow).where(Escrow.status == EscrowStatus.refunded))).scalar() or 0
    disputed_count = (await db.execute(select(func.count()).select_from(Escrow).where(Escrow.status == EscrowStatus.disputed))).scalar() or 0
    
    return {
        "items": items,
        "total": total,
        "summary": {
            "held": held_count,
            "released": released_count,
            "refunded": refunded_count,
            "disputed": disputed_count
        }
    }

@router.get("/admin-escrows/{escrow_id}")
async def get_admin_escrow_detail(
    escrow_id: str,
    db: AsyncSession = Depends(get_session),
):
    """Get full details of a specific escrow."""
    from app.models.escrow import Escrow
    from app.models.price_negotiation import PriceNegotiation
    from app.models.services import Service, ServiceCategory, ServiceCategoryLink
    from app.models.posted_job import PostedJob
    from app.models.user import Users
    from app.models.wallet import Wallet
    from app.models.admin import PlatformRevenueLog
    from app.services.fee_service import fee_service
    from sqlmodel import select
    from sqlalchemy.orm import aliased
    
    try:
        eid = uuid.UUID(escrow_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid escrow_id")
        
    PayerWallet = aliased(Wallet)
    PayerUser = aliased(Users)
    PayeeWallet = aliased(Wallet)
    PayeeUser = aliased(Users)
    
    stmt = select(Escrow, PriceNegotiation, Service, PostedJob, PayerUser, PayeeUser, ServiceCategory)\
        .outerjoin(PriceNegotiation, Escrow.payment_negotiation_id == PriceNegotiation.id)\
        .outerjoin(Service, PriceNegotiation.service_id == Service.id)\
        .outerjoin(PostedJob, PriceNegotiation.posted_job_id == PostedJob.id)\
        .outerjoin(ServiceCategoryLink, Service.id == ServiceCategoryLink.service_id)\
        .outerjoin(ServiceCategory, ServiceCategoryLink.category_id == ServiceCategory.id)\
        .outerjoin(PayerWallet, Escrow.payer_wallet_id == PayerWallet.id)\
        .outerjoin(PayerUser, PayerWallet.user_id == PayerUser.id)\
        .outerjoin(PayeeWallet, Escrow.payee_wallet_id == PayeeWallet.id)\
        .outerjoin(PayeeUser, PayeeWallet.user_id == PayeeUser.id)\
        .where(Escrow.id == eid)
        
    res = await db.execute(stmt)
    result = res.first()
    
    if not result:
        raise HTTPException(status_code=404, detail="Escrow not found")
        
    esc, neg, svc, p_job, payer, payee, cat = result
    service_name = svc.name if svc else (p_job.title if p_job else "Escrow Service")
    service_desc = svc.description if svc else (p_job.description if p_job else "Direct escrow payment")
    service_price = f"₦{svc.price:,.2f}" if svc else f"₦{esc.amount_cents / 100:,.2f}"

    # Platform fee & net released payout calculation
    fee_log_stmt = select(PlatformRevenueLog).where(
        PlatformRevenueLog.reference == str(esc.id),
        PlatformRevenueLog.event_type == "escrow_release"
    )
    fee_log_res = await db.execute(fee_log_stmt)
    fee_log = fee_log_res.scalar_one_or_none()

    if fee_log:
        fee_cents = fee_log.fee_amount_cents
    else:
        fee_config = await fee_service.get_fee_config(db)
        if fee_config.escrow_release_fee_enabled:
            fee_cents = fee_service.calculate_fee(
                esc.amount_cents,
                fee_config.escrow_release_fee_type,
                fee_config.escrow_release_fee_value
            )
        else:
            fee_cents = 0

    net_released_cents = max(0, esc.amount_cents - fee_cents)
    
    return {
        "id": str(esc.id),
        "amount": f"₦{esc.amount_cents / 100:,.2f}",
        "fee_amount": f"₦{fee_cents / 100:,.2f}",
        "released_amount": f"₦{net_released_cents / 100:,.2f}",
        "fee_cents": fee_cents,
        "net_released_cents": net_released_cents,
        "status": esc.status.value.upper() if hasattr(esc.status, "value") else str(esc.status).upper(),
        "created_at": esc.created_at.strftime("%d/%m/%Y %H:%M:%S") if esc.created_at else "—",
        "updated_at": esc.updated_at.strftime("%d/%m/%Y %H:%M:%S") if esc.updated_at else "—",
        "service": {
            "name": service_name,
            "category": cat.name if cat else "General",
            "description": service_desc,
            "price": service_price
        },
        "negotiation": {
            "proposed_price": f"₦{neg.proposed_price_cents / 100:,.2f}" if neg else f"₦{esc.amount_cents / 100:,.2f}",
            "original_price": service_price,
            "status": neg.status.value if (neg and hasattr(neg.status, "value")) else "completed"
        },
        "payer": {
            "username": payer.username if payer else "Payer",
            "email": payer.email if payer else "N/A",
            "full_name": payer.username if payer else "Payer"
        },
        "payee": {
            "username": payee.username if payee else "Payee",
            "email": payee.email if payee else "N/A",
            "full_name": payee.username if payee else "Payee"
        }
    }

@router.post("/admin-escrows/{escrow_id}/status")
async def update_admin_escrow_status(
    escrow_id: str,
    payload: dict,
    db: AsyncSession = Depends(get_session),
):
    """Manually update escrow status with wallet ledger balance adjustments."""
    from app.models.escrow import Escrow, EscrowStatus
    
    try:
        eid = uuid.UUID(escrow_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid escrow_id")
        
    new_status = payload.get("status")
    if not new_status or new_status.lower() not in ["held", "released", "refunded", "disputed"]:
        raise HTTPException(status_code=400, detail="Invalid status")
        
    esc = await db.get(Escrow, eid)
    if not esc:
        raise HTTPException(status_code=404, detail="Escrow not found")
        
    target_status = EscrowStatus(new_status.lower())
    if esc.status != target_status:
        from app.services.escrow_service import EscrowService
        esc_service = EscrowService(db)
        
        if esc.status in (EscrowStatus.held, EscrowStatus.disputed) and target_status == EscrowStatus.released:
            # Retrieve payer user context
            from app.models.wallet import Wallet
            payer_w = await db.get(Wallet, esc.payer_wallet_id)
            admin_user = type("AdminUser", (), {"id": payer_w.user_id if payer_w else esc.payer_wallet_id})()
            await esc_service.release_escrow(user=admin_user, escrow_id=esc.id)
        elif esc.status in (EscrowStatus.held, EscrowStatus.disputed) and target_status == EscrowStatus.refunded:
            from app.models.wallet import Wallet
            payer_w = await db.get(Wallet, esc.payer_wallet_id)
            admin_user = type("AdminUser", (), {"id": payer_w.user_id if payer_w else esc.payer_wallet_id})()
            await esc_service.refund_escrow(user=admin_user, escrow_id=esc.id)
        else:
            esc.status = target_status
            db.add(esc)
            await db.commit()
            
            # Send notification to both parties for direct admin status updates
            try:
                from app.models.wallet import Wallet
                from app.models.user import Users
                payer_w = await db.get(Wallet, esc.payer_wallet_id)
                payee_w = await db.get(Wallet, esc.payee_wallet_id)
                payer_u = await db.get(Users, payer_w.user_id) if payer_w else None
                payee_u = await db.get(Users, payee_w.user_id) if payee_w else None
                
                if target_status == EscrowStatus.disputed:
                    esc_service.notifier.send_escrow_dispute_mail(payer_u, payee_u, esc)
                else:
                    esc_service.notifier.send_escrow_status_change_mail(payer_u, payee_u, esc, target_status.value)
            except Exception as mail_err:
                print(f"Failed to dispatch admin status change email: {mail_err}")
        
    return {"message": f"Escrow status updated to {new_status.upper()}"}


@router.get("/admin-transactions")
async def list_admin_transactions(
    page: int = 1,
    limit: int = 50,
    db: AsyncSession = Depends(get_session),
):
    """List all transactions across the platform."""
    from app.models.transactions import Transaction, TxnStatus
    from app.models.user import Users
    from sqlmodel import select, func
    from datetime import datetime, timezone
    
    stmt = select(Transaction, Users).join(Users, Transaction.users_id == Users.id)
    
    total_res = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = total_res.scalar() or 0
    
    stmt = stmt.order_by(Transaction.created_at.desc()).offset((page - 1) * limit).limit(limit)
    res = await db.execute(stmt)
    rows = res.all()
    
    items = []
    for txn, user in rows:
        items.append({
            "id": str(txn.id),
            "user_name": user.username,
            "type": txn.type.value.upper(),
            "amount": f"\u20a6{txn.amount_cents / 100:,.2f}",
            "status": txn.status.value.upper(),
            "reference": txn.reference,
            "created_at": txn.created_at.strftime("%d/%m/%Y - %I:%M %p") if txn.created_at else "\u2014",
        })
        
    # Summary stats for transactions
    total_volume = (await db.execute(select(func.sum(Transaction.amount_cents)).where(Transaction.status == TxnStatus.completed))).scalar() or 0
    today_volume = (await db.execute(select(func.sum(Transaction.amount_cents)).where(Transaction.status == TxnStatus.completed, Transaction.created_at >= datetime.now(timezone.utc).replace(hour=0, minute=0, second=0)))).scalar() or 0
    
    return {
        "items": items,
        "total": total,
        "summary": {
            "total_volume": f"\u20a6{total_volume / 100:,.2f}",
            "today_volume": f"\u20a6{today_volume / 100:,.2f}",
            "count": total
        }
    }

@router.get("/admin-transactions/{transaction_id}")
async def get_admin_transaction_detail(
    transaction_id: str,
    db: AsyncSession = Depends(get_session),
):
    """Get full details of a specific transaction."""
    from app.models.transactions import Transaction
    from app.models.user import Users
    from app.models.wallet import Wallet
    from sqlmodel import select
    
    try:
        tid = uuid.UUID(transaction_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid transaction_id")
        
    stmt = select(Transaction, Users, Wallet)\
        .join(Users, Transaction.users_id == Users.id)\
        .join(Wallet, Transaction.wallet_id == Wallet.id)\
        .where(Transaction.id == tid)
        
    res = await db.execute(stmt)
    result = res.first()
    
    if not result:
        raise HTTPException(status_code=404, detail="Transaction not found")
        
    txn, user, wallet = result
    
    return {
        "id": str(txn.id),
        "amount": f"\u20a6{txn.amount_cents / 100:,.2f}",
        "status": txn.status.value.upper(),
        "type": txn.type.value.upper(),
        "reference": txn.reference,
        "created_at": txn.created_at.strftime("%d/%m/%Y %H:%M:%S") if txn.created_at else "\u2014",
        "updated_at": txn.updated_at.strftime("%d/%m/%Y %H:%M:%S") if txn.updated_at else "\u2014",
        "user": {
            "username": user.username,
            "email": user.email,
        },
        "wallet": {
            "id": str(wallet.id),
            "balance": f"\u20a6{wallet.balance_cents / 100:,.2f}" if hasattr(wallet, "balance_cents") else "\u2014"
        }
    }
@router.get("/admin-tickets")
async def get_admin_tickets(
    db: AsyncSession = Depends(get_session),
):
    """List all support tickets for admin view with user details."""
    from app.services.support_service import SupportTicketService
    service = SupportTicketService(db)
    return await service.list_tickets(is_admin=True)

@router.get("/admin-tickets/{ticket_id}/replies")
async def get_admin_ticket_replies(
    ticket_id: str,
    db: AsyncSession = Depends(get_session),
):
    """List replies for a specific ticket with author names."""
    from app.services.support_service import SupportTicketService
    try:
        tid = uuid.UUID(ticket_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ticket_id")
        
    service = SupportTicketService(db)
    return await service.list_replies(tid)

@router.get("/admin-tickets/{ticket_id}")
async def get_admin_ticket(
    ticket_id: str,
    db: AsyncSession = Depends(get_session),
):
    """Get full details of a specific ticket."""
    from app.models.support_ticket import SupportTicket
    from app.models.user import Users
    from app.models.profile import Profile
    from sqlmodel import select
    
    try:
        tid = uuid.UUID(ticket_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ticket_id")
        
    query = (
        select(SupportTicket, Users.username, Users.email, Profile.first_name, Profile.last_name)
        .outerjoin(Users, SupportTicket.user_id == Users.id)
        .outerjoin(Profile, Users.id == Profile.user_id)
        .where(SupportTicket.id == tid)
    )
    res = await db.execute(query)
    row = res.first()
    if not row:
        raise HTTPException(status_code=404, detail="Ticket not found")
        
    ticket, username, email, first_name, last_name = row
    t_dict = ticket.model_dump()
    full_name = f"{first_name} {last_name}".strip() if (first_name or last_name) else None
    t_dict["user_name"] = full_name or username or email or "User"
    t_dict["user_email"] = email
    return t_dict



# ════════════════════════════════════════════════════════════════════════════
#  ADMIN PAYMENT MANAGEMENT ENDPOINTS
# ════════════════════════════════════════════════════════════════════════════

@router.get("/payment-settings")
async def get_payment_settings(db: AsyncSession = Depends(get_session)):
    """Return the current platform payment settings."""
    from app.services.payment_service import get_payment_settings as _get_settings
    settings = await _get_settings(db)
    return {
        "id": settings.id,
        "auto_approve_withdrawals": settings.auto_approve_withdrawals,
        "screen_deposits": settings.screen_deposits,
        "updated_at": settings.updated_at.isoformat() if settings.updated_at else None,
    }


@router.put("/payment-settings")
async def update_payment_settings(
    req: Request,
    db: AsyncSession = Depends(get_session),
):
    """Update platform-wide payment settings (auto-approve, deposit screening)."""
    from app.services.payment_service import update_payment_settings as _update_settings
    try:
        body = await req.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    auto_approve = body.get("auto_approve_withdrawals")
    screen = body.get("screen_deposits")

    settings = await _update_settings(db, auto_approve, screen)
    return {
        "id": settings.id,
        "auto_approve_withdrawals": settings.auto_approve_withdrawals,
        "screen_deposits": settings.screen_deposits,
        "updated_at": settings.updated_at.isoformat() if settings.updated_at else None,
    }


@router.get("/withdrawals")
async def list_withdrawals(
    status: Optional[str] = None,
    page: int = 1,
    limit: int = 50,
    db: AsyncSession = Depends(get_session),
):
    """List all withdrawal requests with optional status filter."""
    from sqlmodel import select, func
    from app.models.payment_request import WithdrawalRequest, WithdrawalStatus, UserBankAccount
    from app.models.user import Users

    stmt = select(WithdrawalRequest)
    if status:
        try:
            stmt = stmt.where(WithdrawalRequest.status == WithdrawalStatus(status.lower()))
        except ValueError:
            pass

    total_res = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = total_res.scalar() or 0

    stmt = stmt.order_by(WithdrawalRequest.created_at.desc()).offset((page - 1) * limit).limit(limit)
    res = await db.execute(stmt)
    withdrawals = res.scalars().all()

    rows = []
    for w in withdrawals:
        user_res = await db.execute(select(Users).where(Users.id == w.user_id))
        user = user_res.scalar_one_or_none()

        bank_res = await db.execute(select(UserBankAccount).where(UserBankAccount.id == w.bank_account_id))
        bank = bank_res.scalar_one_or_none()

        rows.append({
            "id": str(w.id),
            "user_id": str(w.user_id),
            "user_email": user.email if user else None,
            "user_name": user.username if user else None,
            "amount_cents": w.amount_cents,
            "amount": f"₦{w.amount_cents / 100:,.2f}",
            "currency": w.currency,
            "status": w.status.value,
            "rejection_reason": w.rejection_reason,
            "bank_account_number": bank.account_number if bank else None,
            "bank_account_name": bank.account_name if bank else None,
            "bank_name": bank.bank_name if bank else None,
            "monnify_reference": w.monnify_reference,
            "reviewed_at": w.reviewed_at.isoformat() if w.reviewed_at else None,
            "created_at": w.created_at.isoformat() if w.created_at else None,
        })

    return {"withdrawals": rows, "total": total, "page": page, "limit": limit}


@router.post("/withdrawals/{withdrawal_id}/approve")
async def approve_withdrawal(
    withdrawal_id: str,
    db: AsyncSession = Depends(get_session),
):
    """Approve a pending withdrawal — triggers Monnify disbursement."""
    from app.services.payment_service import admin_approve_withdrawal
    try:
        wid = uuid.UUID(withdrawal_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid withdrawal_id")

    withdrawal = await admin_approve_withdrawal(db, wid, None)
    return {"message": "Withdrawal approved and transfer initiated", "status": withdrawal.status.value}


@router.post("/withdrawals/{withdrawal_id}/reject")
async def reject_withdrawal(
    withdrawal_id: str,
    req: Request,
    db: AsyncSession = Depends(get_session),
):
    """Reject a pending withdrawal with a reason."""
    from app.services.payment_service import admin_reject_withdrawal
    try:
        wid = uuid.UUID(withdrawal_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid withdrawal_id")

    try:
        body = await req.json()
    except Exception:
        body = {}

    reason = body.get("reason", "No reason provided") if isinstance(body, dict) else "No reason provided"
    withdrawal = await admin_reject_withdrawal(db, wid, None, reason)
    return {"message": "Withdrawal rejected", "status": withdrawal.status.value}


@router.get("/deposits")
async def list_deposits(
    status: Optional[str] = None,
    page: int = 1,
    limit: int = 50,
    db: AsyncSession = Depends(get_session),
):
    """List all deposit requests. Use status=screened_pending to see the review queue."""
    from sqlmodel import select, func
    from app.models.payment_request import DepositRequest, DepositStatus
    from app.models.user import Users

    stmt = select(DepositRequest)
    if status:
        try:
            stmt = stmt.where(DepositRequest.status == DepositStatus(status.lower()))
        except ValueError:
            pass

    total_res = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = total_res.scalar() or 0

    stmt = stmt.order_by(DepositRequest.created_at.desc()).offset((page - 1) * limit).limit(limit)
    res = await db.execute(stmt)
    deposits = res.scalars().all()

    rows = []
    for d in deposits:
        user_res = await db.execute(select(Users).where(Users.id == d.user_id))
        user = user_res.scalar_one_or_none()

        rows.append({
            "id": str(d.id),
            "user_id": str(d.user_id),
            "user_email": user.email if user else None,
            "user_name": user.username if user else None,
            "amount_cents": d.amount_cents,
            "amount": f"₦{d.amount_cents / 100:,.2f}",
            "currency": d.currency,
            "status": d.status.value,
            "monnify_reference": d.monnify_reference,
            "payment_link": d.payment_link,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        })

    return {"deposits": rows, "total": total, "page": page, "limit": limit}


@router.post("/deposits/{deposit_id}/approve")
async def approve_deposit(
    deposit_id: str,
    db: AsyncSession = Depends(get_session),
):
    """Approve a screened (held) deposit — credits user's wallet."""
    from app.services.payment_service import admin_approve_deposit
    try:
        did = uuid.UUID(deposit_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid deposit_id")

    admin_id = uuid.uuid4()  # Replace with get_current_admin().id when wired
    deposit = await admin_approve_deposit(db, did, admin_id)
    return {"message": "Deposit approved and wallet credited", "status": deposit.status.value}


@router.get("/fee-config")
async def get_fee_config(db: AsyncSession = Depends(get_session)):
    from app.services.fee_service import fee_service
    config = await fee_service.get_fee_config(db)
    return config


@router.put("/fee-config")
async def update_fee_config(
    req: Request,
    db: AsyncSession = Depends(get_session),
):
    from app.services.fee_service import fee_service
    config = await fee_service.get_fee_config(db)
    try:
        body = await req.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    for k, v in body.items():
        if hasattr(config, k):
            setattr(config, k, v)

    config.updated_at = datetime.now(timezone.utc)
    db.add(config)
    await db.commit()
    await db.refresh(config)
    return config


@router.get("/revenue")
async def get_platform_revenue(
    page: int = 1,
    limit: int = 50,
    event_type: Optional[str] = None,
    db: AsyncSession = Depends(get_session),
):
    from sqlmodel import select, func
    from app.models.admin import PlatformRevenueLog
    from app.models.user import Users

    # 1. Total revenue stats
    # All time
    all_time_stmt = select(func.sum(PlatformRevenueLog.fee_amount_cents))
    all_time_res = await db.execute(all_time_stmt)
    total_all_time = all_time_res.scalar() or 0

    # This month
    now = datetime.now(timezone.utc)
    start_of_month = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    month_stmt = select(func.sum(PlatformRevenueLog.fee_amount_cents)).where(PlatformRevenueLog.created_at >= start_of_month)
    month_res = await db.execute(month_stmt)
    total_this_month = month_res.scalar() or 0

    # Today
    start_of_today = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    today_stmt = select(func.sum(PlatformRevenueLog.fee_amount_cents)).where(PlatformRevenueLog.created_at >= start_of_today)
    today_res = await db.execute(today_stmt)
    total_today = today_res.scalar() or 0

    # 2. Get paginated revenue logs
    stmt = select(PlatformRevenueLog)
    if event_type:
        stmt = stmt.where(PlatformRevenueLog.event_type == event_type)

    total_count_res = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total_count = total_count_res.scalar() or 0

    stmt = stmt.order_by(PlatformRevenueLog.created_at.desc()).offset((page - 1) * limit).limit(limit)
    res = await db.execute(stmt)
    logs = res.scalars().all()

    rows = []
    for log in logs:
        user_res = await db.execute(select(Users).where(Users.id == log.user_id))
        user = user_res.scalar_one_or_none()
        rows.append({
            "id": str(log.id),
            "event_type": log.event_type,
            "user_id": str(log.user_id),
            "user_email": user.email if user else None,
            "user_name": user.username if user else None,
            "gross_amount_cents": log.gross_amount_cents,
            "gross_amount": f"₦{log.gross_amount_cents / 100:,.2f}",
            "fee_amount_cents": log.fee_amount_cents,
            "fee_amount": f"₦{log.fee_amount_cents / 100:,.2f}",
            "fee_type": log.fee_type,
            "fee_value": log.fee_value,
            "reference": log.reference,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        })

    # Category breakdown stats
    escrow_rev = (await db.execute(select(func.sum(PlatformRevenueLog.fee_amount_cents)).where(PlatformRevenueLog.event_type == "escrow_release"))).scalar() or 0
    deposit_rev = (await db.execute(select(func.sum(PlatformRevenueLog.fee_amount_cents)).where(PlatformRevenueLog.event_type == "deposit"))).scalar() or 0
    withdrawal_rev = (await db.execute(select(func.sum(PlatformRevenueLog.fee_amount_cents)).where(PlatformRevenueLog.event_type == "withdrawal"))).scalar() or 0

    return {
        "revenue_logs": rows,
        "total_count": total_count,
        "page": page,
        "limit": limit,
        "stats": {
            "total_all_time": total_all_time,
            "total_this_month": total_this_month,
            "total_today": total_today,
            "total_escrow_revenue": escrow_rev,
            "total_deposit_revenue": deposit_rev,
            "total_withdrawal_revenue": withdrawal_rev,
            "total_all_time_formatted": f"₦{total_all_time / 100:,.2f}",
            "total_this_month_formatted": f"₦{total_this_month / 100:,.2f}",
            "total_today_formatted": f"₦{total_today / 100:,.2f}",
            "total_escrow_revenue_formatted": f"₦{escrow_rev / 100:,.2f}",
            "total_deposit_revenue_formatted": f"₦{deposit_rev / 100:,.2f}",
            "total_withdrawal_revenue_formatted": f"₦{withdrawal_rev / 100:,.2f}",
        }
    }


# ──────────────────────────────────────────────
#  ADMIN-FACING POSTED JOBS MANAGEMENT ENDPOINTS
# ──────────────────────────────────────────────

@router.get("/admin-posted-jobs")
async def list_admin_posted_jobs(
    search: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    limit: int = 50,
    db: AsyncSession = Depends(get_session),
):
    """Return paginated list of all posted jobs on the platform."""
    from app.models.posted_job import PostedJob, PostedJobStatus
    from app.models.user import Users
    from app.models.services import ServiceCategory
    from sqlmodel import select, func
    from sqlalchemy.orm import selectinload

    stmt = select(PostedJob).options(selectinload(PostedJob.user), selectinload(PostedJob.category))
    if search:
        stmt = stmt.where(
            (PostedJob.title.ilike(f"%{search}%")) | (PostedJob.description.ilike(f"%{search}%"))
        )
    if status:
        try:
            stmt = stmt.where(PostedJob.status == PostedJobStatus(status.lower()))
        except Exception:
            pass

    total_res = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = total_res.scalar() or 0

    stmt = stmt.order_by(PostedJob.created_at.desc()).offset((page - 1) * limit).limit(limit)
    result = await db.execute(stmt)
    jobs = result.scalars().all()

    rows = []
    for j in jobs:
        # count bid negotiations
        from app.models.price_negotiation import PriceNegotiation
        bid_res = await db.execute(
            select(func.count()).select_from(PriceNegotiation).where(PriceNegotiation.posted_job_id == j.id)
        )
        bid_count = bid_res.scalar() or 0

        rows.append({
            "id": str(j.id),
            "title": j.title,
            "description": j.description,
            "user_id": str(j.user_id),
            "username": j.user.username if j.user else "Anonymous",
            "category": j.category.name if j.category else "General",
            "min_price": j.min_price_cents / 100.0,
            "max_price": j.max_price_cents / 100.0,
            "min_price_formatted": f"₦{j.min_price_cents / 100:,.2f}",
            "max_price_formatted": f"₦{j.max_price_cents / 100:,.2f}",
            "status": j.status.value.upper() if hasattr(j.status, "value") else str(j.status).upper(),
            "listed": j.created_at.strftime("%d/%m/%Y") if j.created_at else "",
            "created_at_iso": j.created_at.isoformat() if j.created_at else "",
            "bid_count": bid_count,
        })

    return {"posted_jobs": rows, "total": total, "page": page, "limit": limit}


@router.post("/posted-jobs/status")
async def change_posted_job_status(
    request: Request,
    job_id: Optional[str] = Form(None),
    status: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_session)
):
    from app.models.posted_job import PostedJob, PostedJobStatus
    from sqlmodel import select

    if not job_id or not status:
        try:
            body = await request.json()
            job_id = job_id or body.get("job_id") or body.get("jobId")
            status = status or body.get("status")
        except Exception:
            pass

    if not job_id or not status:
        raise HTTPException(status_code=400, detail="Missing job_id or status")

    try:
        job_uuid = uuid.UUID(job_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid job_id format")

    stmt = select(PostedJob).where(PostedJob.id == job_uuid)
    res = await db.execute(stmt)
    job = res.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Posted job not found")

    if status.upper() == "DELETE":
        await db.delete(job)
        await db.commit()
        return {"message": "Posted job deleted successfully"}

    try:
        # Status can be open, assigned, completed, cancelled
        stat_lower = status.lower()
        if stat_lower in [s.value for s in PostedJobStatus]:
            job.status = PostedJobStatus(stat_lower)
            await db.commit()
            await db.refresh(job)
            return {"message": "Status updated successfully", "status": job.status.value.upper()}
        else:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


