# app/schemas/work_submission.py
from datetime import datetime
from typing import List, Optional
from uuid import UUID
from fastapi import Form
from pydantic import BaseModel
from fastapi import Form

class WorkSubmissionCreate(BaseModel):
    user_id: Optional[UUID] = None
    escrow_id: UUID
    service_id: UUID
    text: Optional[str] = None
    links: Optional[List[str]] = None
    image_urls: Optional[List[str]] = None
    file_urls: Optional[List[str]] = None

    @classmethod
    def as_form(
        cls,
        escrow_id: UUID = Form(...),
        service_id: UUID = Form(...),
        text: Optional[str] = Form(None),
        links: Optional[str] = Form(None),
    ):
        """
        Helper to parse form fields into the Pydantic model.
        `links` can be JSON array string or comma-separated string.
        Files are handled separately (UploadFile).
        """
        parsed_links = None
        if links:
            import json
            try:
                parsed_links = json.loads(links)
            except Exception:
                parsed_links = [x.strip() for x in links.split(",") if x.strip()]

        return cls(
            escrow_id=escrow_id,
            service_id=service_id,
            text=text,
            links=parsed_links,
        )


from app.schemas.services import ServiceRead

class WorkSubmissionRead(BaseModel):
    id: UUID
    user_id: UUID
    escrow_id: UUID
    service_id: UUID
    text: Optional[str]
    links: Optional[List[str]]
    image_urls: Optional[List[str]]
    file_urls: Optional[List[str]]
    created_at: datetime
    service: Optional[ServiceRead] = None

    class Config:
        from_attributes = True
