from pydantic import BaseModel
from typing import Optional, List
import uuid
from datetime import datetime
from app.models.services import ServiceType, ServiceStatus


class CategoryRead(BaseModel):
    id: uuid.UUID
    name: str

    class Config:
        from_attributes = True


class ServiceCreate(BaseModel):
    name: str
    description: str
    price: float
    discount: Optional[bool] = False
    discount_percent: Optional[float] = 0.0
    type: ServiceType
    meta_tags: Optional[str] = None
    keywords: Optional[str] = None
    category_ids: Optional[List[uuid.UUID]] = None


class ServiceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = 0.00
    discount: Optional[bool] = False
    discount_percent: Optional[float] = 0.0
    type: Optional[ServiceType] = None
    meta_tags: Optional[str] = None
    keywords: Optional[str] = None
    category_ids: Optional[List[uuid.UUID]] = None


class ServiceRead(BaseModel):
    id: uuid.UUID
    name: str
    description: str
    price: float
    discount: Optional[bool] = False
    discount_percent: Optional[float] = 0.0
    type: ServiceType
    username: str
    user_id: uuid.UUID
    upvotes: int
    status: ServiceStatus
    image: Optional[str] = None
    image_alt: Optional[str] = None
    created_at: datetime
    categories: List[CategoryRead] = []

    class Config:
        from_attributes = True
