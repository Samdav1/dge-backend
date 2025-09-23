import enum
import uuid
from datetime import date, datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship, SQLModel



class KYCStatus(str, enum.Enum):
    """The lifecycle of a KYC verification."""
    unverified = "unverified"
    pending = "pending"
    verified = "verified"
    rejected = "rejected"


class DocumentType(str, enum.Enum):
    """Type of document submitted."""
    passport = "passport"
    drivers_license = "drivers_license"
    national_id = "national_id"
    utility_bill = "utility_bill"
    bank_statement = "bank_statement"


class KYC(SQLModel, table=True):
    user_id: uuid.UUID = Field(foreign_key="users.id", primary_key=True)
    team_user_id: Optional[uuid.UUID] = Field(foreign_key="teams.id", index=True)
    status: KYCStatus = Field(default=KYCStatus.unverified, nullable=False, index=True)
    first_name: Optional[str] = Field(default=None)
    last_name: Optional[str] = Field(default=None)
    date_of_birth: Optional[date] = Field(default=None)
    nationality: Optional[str] = Field(default=None)
    address_line_1: Optional[str] = Field(default=None)
    city: Optional[str] = Field(default=None)
    country: Optional[str] = Field(default=None)
    postal_code: Optional[str] = Field(default=None)
    id_document_type: Optional[DocumentType] = Field(default=None)
    id_document_s3_key: Optional[str] = Field(default=None)
    address_document_type: Optional[DocumentType] = Field(default=None)
    address_document_s3_key: Optional[str] = Field(default=None)
    rejection_reason: Optional[str] = Field(default=None)
    reviewed_by_id: Optional[uuid.UUID] = Field(default=None, foreign_key="teamusers.id")
    submitted_at: Optional[datetime] = Field(default=None)
    reviewed_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), sa_column_kwargs={"onupdate": datetime.now(timezone.utc)})

    user: "Users" = Relationship(back_populates="kyc")
    reviewed_by: Optional["TeamUser"] = Relationship(back_populates="team_user")