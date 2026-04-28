from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List
from datetime import datetime
import uuid
from enum import Enum


class PortfolioVisibility(str, Enum):
    public = "public"
    private = "private"


class UserPortfolioBase(BaseModel):
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    visibility: PortfolioVisibility = PortfolioVisibility.public
    website: Optional[HttpUrl] = None
    facebook: Optional[HttpUrl] = None
    twitter: Optional[HttpUrl] = None
    youtube: Optional[HttpUrl] = None
    instagram: Optional[HttpUrl] = None


class UserPortfolioCreate(UserPortfolioBase):
    pass


class UserPortfolioUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    visibility: Optional[PortfolioVisibility] = None
    website: Optional[HttpUrl] = None
    facebook: Optional[HttpUrl] = None
    twitter: Optional[HttpUrl] = None
    youtube: Optional[HttpUrl] = None
    instagram: Optional[HttpUrl] = None


class UserPortfolioRead(UserPortfolioBase):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    # media_files: List["PortfolioMediaRead"] = []
    # reviews: List["ReviewRead"] = []

    class Config:
        from_attributes = True

class PortfolioMediaBase(BaseModel):
    media_type: str
    s3_key: str
    thumbnail_s3_key: Optional[str] = None
    size_bytes: Optional[int] = None
    processed: bool = False


class PortfolioMediaCreate(PortfolioMediaBase):
    pass


class PortfolioMediaUpdate(BaseModel):
    media_type: Optional[str] = None
    s3_key: Optional[str] = None
    thumbnail_s3_key: Optional[str] = None
    size_bytes: Optional[int] = None
    processed: Optional[bool] = None


class PortfolioMediaRead(PortfolioMediaBase):
    id: uuid.UUID
    portfolio_id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True


class ReviewBase(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    comment: str


class ReviewCreate(ReviewBase):
    pass


class ReviewUpdate(BaseModel):
    rating: Optional[int] = Field(None, ge=1, le=5)
    comment: Optional[str] = None


class ReviewRead(ReviewBase):
    id: uuid.UUID
    user_id: uuid.UUID
    portfolio_id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True


UserPortfolioRead.model_rebuild()
PortfolioMediaRead.model_rebuild()
ReviewRead.model_rebuild()