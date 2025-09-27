import uuid
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import Column, String, UUID, TIMESTAMP, ForeignKey, Integer
from sqlmodel import SQLModel, Field, Relationship, Text
import enum
from sqlalchemy import Enum as SAEnum


class ServiceStatus(str, enum.Enum):
    draft = "draft"
    pending_review = "pending_review"
    approved = "approved"
    rejected = "rejected"

class ServiceType(str, enum.Enum):
    physical = "physical"
    online = "online"
    hybrid = "hybrid"

class ServiceCategoryLink(SQLModel, table=True):
    __tablename__ = "service_category_link"

    service_id: uuid.UUID = Field(
        sa_column=Column(UUID(as_uuid=True), ForeignKey("services.id"), primary_key=True)
    )
    category_id: uuid.UUID = Field(
        sa_column=Column(UUID(as_uuid=True), ForeignKey("service_categories.id"), primary_key=True)
    )

class ServiceCategory(SQLModel, table=True):
    __tablename__ = "service_categories"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, unique=True, nullable=False),
    )
    name: str = Field(sa_column=Column(String(100), nullable=False, unique=True, index=True))
    description: Optional[str] = Field(sa_column=Column(Text, nullable=True))
    icon: Optional[str] = Field(default=None)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True), nullable=False),
    )

    services: List["Service"] = Relationship(
        back_populates="categories",
        link_model=ServiceCategoryLink
    )


class Service(SQLModel, table=True):
    __tablename__ = "services"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, unique=True, nullable=False),
    )
    name: str = Field(sa_column=Column(String(255), nullable=False, index=True))
    description: str = Field(sa_column=Column(Text, nullable=False))
    type: ServiceType = Field(sa_column=Column(SAEnum(ServiceType, name="service_type_enum"), nullable=False, default=ServiceType.online))
    username: str = Field(sa_column=Column(String(150), nullable=False, index=True))
    user_id: uuid.UUID = Field(sa_column=Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False))
    upvotes: int = Field(sa_column=Column(Integer, default=0, nullable=False))
    meta_tags: Optional[str] = Field(default=None)
    keywords: Optional[str] = Field(default=None)
    image: Optional[str] = Field(default=None)
    image_alt: Optional[str] = Field(default=None)
    user_online: bool = Field(default=False)
    user_picture: Optional[str] = Field(default=None)
    status: ServiceStatus = Field(sa_column=Column(SAEnum(ServiceStatus, name="service_status_enum"), default="draft", nullable=False))
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True), nullable=False),
    )
    categories: List["ServiceCategory"] = Relationship(
        back_populates="services",
        link_model=ServiceCategoryLink
    )

    user: 'Users' = Relationship(back_populates="services")
    negotiations: 'PriceNegotiation' = Relationship(back_populates="services")
    submissions: "WorkSubmission" = Relationship(back_populates="service")
