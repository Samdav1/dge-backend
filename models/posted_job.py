import uuid
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import Column, String, UUID, TIMESTAMP, ForeignKey, Integer, Enum as SAEnum
from sqlmodel import SQLModel, Field, Relationship, Text
import enum


class PostedJobStatus(str, enum.Enum):
    open = "open"
    assigned = "assigned"
    completed = "completed"
    cancelled = "cancelled"


class PostedJob(SQLModel, table=True):
    __tablename__ = "posted_jobs"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, unique=True, nullable=False),
    )
    user_id: uuid.UUID = Field(
        sa_column=Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    )
    title: str = Field(sa_column=Column(String(255), nullable=False, index=True))
    description: str = Field(sa_column=Column(Text, nullable=False))
    
    category_id: uuid.UUID = Field(
        sa_column=Column(UUID(as_uuid=True), ForeignKey("service_categories.id"), nullable=False, index=True)
    )
    
    min_price_cents: int = Field(sa_column=Column(Integer, nullable=False))
    max_price_cents: int = Field(sa_column=Column(Integer, nullable=False))
    
    image: Optional[str] = Field(sa_column=Column(String(500), nullable=True))
    
    status: PostedJobStatus = Field(
        sa_column=Column(SAEnum(PostedJobStatus, name="posted_job_status_enum"), nullable=False, default=PostedJobStatus.open)
    )

    payment_method: str = Field(
        default="platform",
        sa_column=Column(String(50), nullable=False, server_default="platform")
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True), nullable=False),
    )

    user: "Users" = Relationship(back_populates="posted_jobs")
    category: "ServiceCategory" = Relationship(back_populates="posted_jobs")
    negotiations: List["PriceNegotiation"] = Relationship(back_populates="posted_job")
