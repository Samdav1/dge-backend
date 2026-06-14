from pydantic import BaseModel, Field, HttpUrl, ConfigDict, model_validator
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

    model_config = ConfigDict(from_attributes=True)
class UserPortfolioWithMediaRead(UserPortfolioRead):
    media_files: Optional[List["PortfolioMediaRead"]] = None

class UserPortfolioWithDetailsRead(UserPortfolioWithMediaRead):
    reviews: Optional[List["ReviewRead"]] = None

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

    model_config = ConfigDict(from_attributes=True)
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
    reviewer_name: Optional[str] = None
    reviewer_avatar: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def populate_reviewer_info(cls, data):
        if not isinstance(data, dict):
            user = getattr(data, "user", None)
            reviewer_name = "Anonymous"
            reviewer_avatar = None
            if user:
                profile = getattr(user, "profile", None)
                if profile:
                    first = getattr(profile, "first_name", "") or ""
                    last = getattr(profile, "last_name", "") or ""
                    name = f"{first} {last}".strip()
                    reviewer_name = name if name else getattr(user, "username", "Anonymous")
                    reviewer_avatar = getattr(profile, "avatar_url", None)
                else:
                    reviewer_name = getattr(user, "username", "Anonymous")
            try:
                setattr(data, "reviewer_name", reviewer_name)
                setattr(data, "reviewer_avatar", reviewer_avatar)
            except Exception:
                pass
        return data

UserPortfolioRead.model_rebuild()
UserPortfolioWithMediaRead.model_rebuild()
UserPortfolioWithDetailsRead.model_rebuild()
PortfolioMediaRead.model_rebuild()
ReviewRead.model_rebuild()