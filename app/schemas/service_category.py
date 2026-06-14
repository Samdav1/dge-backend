import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class ServiceCategoryBase(BaseModel):
    name: str
    description: Optional[str] = None
    icon: Optional[str] = None


class ServiceCategoryCreate(ServiceCategoryBase):
    pass


class ServiceCategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None


class ServiceCategoryRead(ServiceCategoryBase):
    id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
# For linking services <-> categories
class ServiceCategoryLinkCreate(BaseModel):
    service_id: uuid.UUID
    category_id: uuid.UUID


class ServiceCategoryLinkRead(BaseModel):
    service_id: uuid.UUID
    category_id: uuid.UUID

    model_config = ConfigDict(from_attributes=True)
