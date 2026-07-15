from pydantic import BaseModel, field_validator, ConfigDict
from datetime import datetime
from typing import Optional
import uuid

from app.models.posted_job import PostedJobStatus


class PostedJobCreate(BaseModel):
    title: str
    description: str
    category_id: uuid.UUID
    min_price_cents: int
    max_price_cents: int
    image: Optional[str] = None
    payment_method: Optional[str] = "platform"

    @field_validator("max_price_cents")
    @classmethod
    def max_must_be_gte_min(cls, v, info):
        if info.data.get("min_price_cents") is not None and v < info.data["min_price_cents"]:
            raise ValueError("max_price_cents must be >= min_price_cents")
        return v


class PostedJobUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    image: Optional[str] = None
    status: Optional[PostedJobStatus] = None


class PostedJobCategoryRead(BaseModel):
    id: uuid.UUID
    name: str
    icon: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
class PostedJobPosterRead(BaseModel):
    id: uuid.UUID
    username: str

    model_config = ConfigDict(from_attributes=True)
class PostedJobRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    description: str
    category_id: uuid.UUID
    min_price_cents: int
    max_price_cents: int
    image: Optional[str] = None
    status: PostedJobStatus
    payment_method: str
    created_at: datetime
    user: Optional[PostedJobPosterRead] = None
    category: Optional[PostedJobCategoryRead] = None
    bid_count: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)
