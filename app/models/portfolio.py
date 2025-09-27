import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import CheckConstraint, SmallInteger
from sqlmodel import SQLModel, Field, Relationship, Column
from enum import Enum

class PortfolioVisibility(str, Enum):
    public = "public"
    private = "private"

class UserPortfolio(SQLModel, table=True):
    """
    Stores user portfolio information.
    Each portfolio entry belongs to a single user.
    """

    __tablename__ = "user_portfolio"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)

    user_id: uuid.UUID = Field(foreign_key="users.id", nullable=False, index=True)

    title: str = Field(nullable=False)
    description: Optional[str] = None
    category: Optional[str] = None

    visibility: PortfolioVisibility = Field(
        default=PortfolioVisibility.public, nullable=False
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), nullable=False
    )

    user: "Users" = Relationship(back_populates="portfolios")
    media_files: list["PortfolioMedia"] = Relationship(back_populates="portfolio")
    reviews: list["Review"] = Relationship(back_populates="portfolio")




class PortfolioMedia(SQLModel, table=True):
    __tablename__ = "portfolio_media"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    portfolio_id: uuid.UUID = Field(foreign_key="user_portfolio.id", nullable=False, index=True)

    media_type: str = Field(nullable=False, description="Type of media (image, video, pdf, etc.)")
    s3_key: str = Field(nullable=False, description="S3 object key for the media file")
    thumbnail_s3_key: Optional[str] = Field(default=None, description="S3 object key for thumbnail preview")
    size_bytes: Optional[int] = Field(default=None, description="File size in bytes")
    processed: bool = Field(default=False, description="Whether the media has been processed (resized, transcoded, etc.)")

    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    portfolio: "UserPortfolio" = Relationship(back_populates="media_files")




class Review(SQLModel, table=True):
    __tablename__ = "reviews"
    __table_args__ = (
        CheckConstraint("rating >= 1 AND rating <= 5", name="check_rating_range"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)

    user_id: uuid.UUID = Field(foreign_key="users.id", nullable=False, index=True)
    portfolio_id: uuid.UUID = Field(foreign_key="user_portfolio.id", nullable=False, index=True)

    rating: int = Field(..., ge=1, le=5, description="The rating from 1 to 5")
    comment: str = Field(nullable=False)

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), nullable=False)

    user: "Users" = Relationship(back_populates="reviews")
    portfolio: "UserPortfolio" = Relationship(back_populates="reviews")
