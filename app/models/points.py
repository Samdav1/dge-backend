import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field, Column, ForeignKey, Relationship
from sqlalchemy import DateTime, BigInteger, func
from uuid import UUID


class AdminPointsSettings(SQLModel, table=True):
    """Configuration table for platform-wide DGE Points settings."""
    __tablename__ = "admin_points_settings"

    id: int = Field(default=1, primary_key=True)
    rate_per_point: float = Field(default=100.0, nullable=False) # Default ₦100 per point
    signup_bonus_points: int = Field(default=10, nullable=False)  # 10 points bonus on signup
    min_purchase_points: int = Field(default=1, nullable=False)
    updated_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False),
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_by_admin_id: Optional[UUID] = Field(default=None, foreign_key="superadmin.id")


class UserPoints(SQLModel, table=True):
    """Tracks each user's current DGE points balance."""
    __tablename__ = "user_points"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(
        sa_column=Column("user_id", ForeignKey("users.id"), nullable=False, unique=True, index=True)
    )
    balance: int = Field(default=10, nullable=False)
    total_earned: int = Field(default=10, nullable=False)
    total_spent: int = Field(default=0, nullable=False)
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False),
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False),
        default_factory=lambda: datetime.now(timezone.utc)
    )


class PointsTransaction(SQLModel, table=True):
    """Audit log of points acquired, spent, or rewarded."""
    __tablename__ = "points_transactions"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(
        sa_column=Column("user_id", ForeignKey("users.id"), nullable=False, index=True)
    )
    points: int = Field(nullable=False)
    naira_amount: float = Field(default=0.0, nullable=False)
    rate_at_time: float = Field(default=100.0, nullable=False)
    type: str = Field(nullable=False)  # "signup_bonus" | "purchase_wallet" | "purchase_gateway" | "spend" | "admin_adjustment"
    status: str = Field(default="successful", nullable=False)  # "successful" | "pending" | "failed"
    reference: str = Field(nullable=False, index=True)
    description: str = Field(nullable=False)
    payment_link: Optional[str] = Field(default=None)
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False),
        default_factory=lambda: datetime.now(timezone.utc)
    )
