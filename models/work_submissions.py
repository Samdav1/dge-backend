# app/models/work_submissions.py
import uuid
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, ForeignKey, JSON, UUID as SA_UUID, TIMESTAMP

class WorkSubmission(SQLModel, table=True):
    __tablename__ = "work_submissions"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(SA_UUID(as_uuid=True), primary_key=True, nullable=False)
    )

    escrow_id: uuid.UUID = Field(
        sa_column=Column("escrow_id", ForeignKey("escrow.id"), nullable=False, index=True, unique=True)
    )
    service_id: uuid.UUID = Field(
        sa_column=Column("service_id", ForeignKey("services.id"), nullable=False, index=True)
    )

    # NEW: who submitted the work
    user_id: uuid.UUID = Field(
        sa_column=Column("user_id", ForeignKey("users.id"), nullable=True, index=True)
    )

    text: str | None = Field(default=None, description="Main submission text")
    links: list[str] | None = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
        description="External links related to submission"
    )
    image_urls: list[str] | None = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
        description="Uploaded images (stored URLs)"
    )
    file_urls: list[str] | None = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
        description="Uploaded files (stored URLs)"
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(TIMESTAMP(timezone=True), nullable=False)
    )

    # relationships (optional; adjust names to match your models)
    escrow: "Escrow" = Relationship(back_populates="submissions")
    service: "Service" = Relationship(back_populates="submissions")
    user: "Users" = Relationship(back_populates="submissions")
