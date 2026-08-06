from datetime import date, datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict
from enum import Enum


class KYCStatus(str, Enum):
    unverified = "unverified"
    pending = "pending"
    verified = "verified"
    rejected = "rejected"


class DocumentType(str, Enum):
    passport = "passport"
    drivers_license = "drivers_license"
    national_id = "national_id"
    utility_bill = "utility_bill"
    bank_statement = "bank_statement"

class KYCBase(BaseModel):
    team_user_id: Optional[UUID] = None
    status: Optional[KYCStatus] = KYCStatus.unverified
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    nationality: Optional[str] = None
    address_line_1: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    id_document_type: Optional[DocumentType] = None
    id_document_s3_key: Optional[str] = None
    id_document_value: Optional[str] = None
    address_document_type: Optional[DocumentType] = None
    address_document_s3_key: Optional[str] = None
    rejection_reason: Optional[str] = None
    reviewed_by_id: Optional[UUID] = None
    submitted_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None
    metamap_verification_id: Optional[str] = None
    metamap_flow_id: Optional[str] = None
    sumsub_applicant_id: Optional[str] = None
    sumsub_inspection_id: Optional[str] = None
    kyc_provider: Optional[str] = "sumsub"


class KYCCreate(KYCBase):
    user_id: UUID


class KYCUpdate(BaseModel):
    team_user_id: Optional[UUID] = None
    status: Optional[KYCStatus] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    nationality: Optional[str] = None
    address_line_1: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    id_document_type: Optional[DocumentType] = None
    id_document_s3_key: Optional[str] = None
    id_document_value: Optional[str] = None
    address_document_type: Optional[DocumentType] = None
    address_document_s3_key: Optional[str] = None
    rejection_reason: Optional[str] = None
    reviewed_by_id: Optional[UUID] = None
    submitted_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None
    metamap_verification_id: Optional[str] = None
    metamap_flow_id: Optional[str] = None
    sumsub_applicant_id: Optional[str] = None
    sumsub_inspection_id: Optional[str] = None
    kyc_provider: Optional[str] = None


class KYCRead(KYCBase):
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
# allows ORM mapping