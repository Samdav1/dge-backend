from datetime import datetime
from uuid import UUID
from typing import Optional
from pydantic import BaseModel, Field, conint, ConfigDict


class ReviewBase(BaseModel):
    rating: conint(ge=1, le=5) = Field(..., description="Rating between 1 and 5")
    comment: str = Field(..., min_length=1)


class ReviewCreate(ReviewBase):
    user_id: Optional[UUID] = None
    portfolio_id: UUID


class ReviewUpdate(BaseModel):
    rating: Optional[conint(ge=1, le=5)]
    comment: Optional[str]


class ReviewRead(ReviewBase):
    id: UUID
    user_id: UUID
    portfolio_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
