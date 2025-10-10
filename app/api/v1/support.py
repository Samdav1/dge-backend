from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession
from uuid import UUID
from app.db.session import get_session
from app.dependencies.auth import get_current_user
from app.schemas.user import UserRead
from app.services.support_service import SupportTicketService
from app.schemas.support_ticket import (
    SupportTicketCreate, SupportTicketUpdate, SupportTicketRead,
    SupportTicketReplyCreate, SupportTicketReplyRead
)


router = APIRouter(prefix="/support-tickets", )


# --- Ticket Endpoints ---
@router.post("/", response_model=SupportTicketRead, status_code=status.HTTP_201_CREATED)
async def create_ticket(payload: SupportTicketCreate, user_id: UserRead = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    service = SupportTicketService(db)
    return await service.create_ticket(payload.dict())

@router.get("/", response_model=list[SupportTicketRead])
async def list_tickets(user_id: UserRead = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    service = SupportTicketService(db)
    return await service.list_tickets()

@router.get("/{ticket_id}", response_model=SupportTicketRead)
async def get_ticket(ticket_id: UUID, user_id: UserRead = Depends(get_current_user),  db: AsyncSession = Depends(get_session)):
    service = SupportTicketService(db)
    try:
        return await service.get_ticket(ticket_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.put("/{ticket_id}", response_model=SupportTicketRead)
async def update_ticket(ticket_id: UUID, payload: SupportTicketUpdate, db: AsyncSession = Depends(get_session)):
    service = SupportTicketService(db)
    try:
        return await service.update_ticket(ticket_id, payload.dict(exclude_unset=True))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.delete("/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ticket(ticket_id: UUID, db: AsyncSession = Depends(get_session)):
    service = SupportTicketService(db)
    try:
        await service.delete_ticket(ticket_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# --- Reply Endpoints ---
@router.post("/{ticket_id}/replies", response_model=SupportTicketReplyRead, status_code=status.HTTP_201_CREATED)
async def create_reply(ticket_id: UUID, payload: SupportTicketReplyCreate, user_id: UserRead = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    service = SupportTicketService(db)
    if str(payload.ticket_id) != str(ticket_id):
        raise HTTPException(status_code=400, detail="Ticket ID mismatch")
    return await service.create_reply(payload.dict())

@router.get("/{ticket_id}/replies", response_model=list[SupportTicketReplyRead])
async def list_replies(ticket_id: UUID, user_id: UserRead = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    service = SupportTicketService(db)
    return await service.list_replies(ticket_id)
