from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel
from app.models.support_ticket import SupportTicketStatus, SupportTicketPriority


class SupportTicketBase(BaseModel):
    subject: str
    description: str
    priority: SupportTicketPriority = SupportTicketPriority.medium


class SupportTicketCreate(SupportTicketBase):
    user_id: UUID


class SupportTicketUpdate(BaseModel):
    subject: Optional[str] = None
    description: Optional[str] = None
    status: Optional[SupportTicketStatus] = None
    priority: Optional[SupportTicketPriority] = None
    assigned_to: Optional[UUID] = None


class SupportTicketRead(SupportTicketBase):
    id: UUID
    user_id: UUID
    assigned_to: Optional[UUID]
    status: SupportTicketStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SupportTicketReplyBase(BaseModel):
    message: str
    attachments: Dict[str, Any] = {}


class SupportTicketReplyCreate(SupportTicketReplyBase):
    ticket_id: UUID
    author_user_id: Optional[UUID] = None
    author_team_user_id: Optional[UUID] = None


class SupportTicketReplyRead(SupportTicketReplyBase):
    id: UUID
    ticket_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True