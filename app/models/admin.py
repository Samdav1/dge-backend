import uuid
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field, ForeignKey, Column
from sqlalchemy import String, DateTime, func
from uuid import UUID
from enum import Enum
from typing import Optional


class AdminRank(str, Enum):
    Major = "Major"
    Minor = "Minor"
    Super = "Super"
    Inspector = "Inspector"
    Support = "Support"
    Manager = "Manager"
    Developer = "Developer"
    Designer = "Designer"
    Analyst = "Analyst"
    Tester = "Tester"
    Product_Owner = "Product Owner"
    Data_Scientist = "Data Scientist"
    Marketer = "Marketer"
    UX_Researcher = "UX Researcher"
    System_Admin = "System Admin"
    Content_Strategist = "Content Strategist"
    Business_Analyst = "Business Analyst"


class AdminStatus(str, Enum):
    Approved = "Approved"
    Rejected = "Rejected"
    Suspended = "Suspended"
    Pending = "Pending"


class SuperAdmin(SQLModel, table=True):
    __tablename__ = "superadmin"

    id: uuid.UUID = Field(primary_key=True, default_factory=uuid.uuid4)
    name: str = Field(nullable=False)
    email: str = Field(
        sa_column=Column(String, unique=True, index=True, nullable=False)
    )
    phone_number: Optional[str] = Field(default=None, unique=True)
    hashed_password: str = Field(nullable=False)
    rank: AdminRank = Field(default=AdminRank.Major, nullable=False)
    status: AdminStatus = Field(default=AdminStatus.Pending, nullable=False)
    is_active: bool = Field(default=True, nullable=False)
    email_verified: bool = Field(default=False, nullable=False)
    phone_verified: bool = Field(default=False, nullable=False)
    mfa_enabled: bool = Field(default=False, nullable=False)
    mfa_secret: Optional[str] = Field(default=None)
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False),
        default_factory=lambda :datetime.now(timezone.utc)
    )
    updated_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            onupdate=func.now(),
            nullable=False
        )
    )
    last_login_at: Optional[datetime] = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False),
        default_factory=lambda :datetime.now(timezone.utc)
    )
    avatar: str = Field(default=None, nullable=False)
    updated_by: Optional[uuid.UUID] = Field(default=None, foreign_key="admin.id")
    
    # Notification Preferences
    email_notifs: bool = Field(default=True, nullable=False)
    push_notifs: bool = Field(default=True, nullable=False)
    security_alerts: bool = Field(default=False, nullable=False)

class AdminSessionStatus(str, Enum):
    CURRENT = "CURRENT"
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"

class AdminSession(SQLModel, table=True):
    __tablename__ = "admin_sessions"

    id: uuid.UUID = Field(primary_key=True, default_factory=uuid.uuid4)
    admin_id: uuid.UUID = Field(foreign_key="superadmin.id", nullable=False)
    device: str = Field(nullable=False)
    location: Optional[str] = Field(default=None)
    ip_address: str = Field(nullable=False)
    status: AdminSessionStatus = Field(default=AdminSessionStatus.CURRENT, nullable=False)
    last_activity: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False),
        default_factory=lambda :datetime.now(timezone.utc)
    )
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False),
        default_factory=lambda :datetime.now(timezone.utc)
    )