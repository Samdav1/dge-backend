from typing import List
from uuid import UUID
from sqlmodel.ext.asyncio.session import AsyncSession
from app.models.support_ticket import SupportTicket, SupportTicketReply
from app.repositories.support_repo import SupportTicketRepository


class SupportTicketService:
    def __init__(self, db: AsyncSession):
        self.repo = SupportTicketRepository(db)

    # --- Tickets ---
    async def create_ticket(self, payload: dict) -> SupportTicket:
        ticket = SupportTicket(**payload)
        return await self.repo.create_ticket(ticket)

    async def get_ticket(self, ticket_id: UUID) -> SupportTicket:
        ticket = await self.repo.get_ticket(ticket_id)
        if not ticket:
            raise ValueError("Ticket not found")
        return ticket

    async def list_tickets(self) -> List[SupportTicket]:
        return await self.repo.list_tickets()

    async def update_ticket(self, ticket_id: UUID, payload: dict) -> SupportTicket:
        ticket = await self.get_ticket(ticket_id)
        return await self.repo.update_ticket(ticket, payload)

    async def delete_ticket(self, ticket_id: UUID) -> None:
        ticket = await self.get_ticket(ticket_id)
        await self.repo.delete_ticket(ticket)

    # --- Replies ---
    async def create_reply(self, payload: dict) -> SupportTicketReply:
        reply = SupportTicketReply(**payload)
        return await self.repo.create_reply(reply)

    async def list_replies(self, ticket_id: UUID) -> List[SupportTicketReply]:
        return await self.repo.list_replies(ticket_id)
