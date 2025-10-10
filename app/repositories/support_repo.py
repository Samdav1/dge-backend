from typing import List, Optional
from uuid import UUID
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from app.models.support_ticket import SupportTicket, SupportTicketReply


class SupportTicketRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # --- Tickets ---
    async def create_ticket(self, ticket: SupportTicket) -> SupportTicket:
        self.db.add(ticket)
        await self.db.commit()
        await self.db.refresh(ticket)
        return ticket

    async def get_ticket(self, ticket_id: UUID) -> Optional[SupportTicket]:
        result = await self.db.execute(select(SupportTicket).where(SupportTicket.id == ticket_id))
        return result.scalars().first()

    async def list_tickets(self) -> List[SupportTicket]:
        result = await self.db.execute(select(SupportTicket))
        return result.scalars().all()

    async def update_ticket(self, ticket: SupportTicket, data: dict) -> SupportTicket:
        for key, value in data.items():
            setattr(ticket, key, value)
        self.db.add(ticket)
        await self.db.commit()
        await self.db.refresh(ticket)
        return ticket

    async def delete_ticket(self, ticket: SupportTicket) -> None:
        await self.db.delete(ticket)
        await self.db.commit()

    async def create_reply(self, reply: SupportTicketReply) -> SupportTicketReply:
        self.db.add(reply)
        await self.db.commit()
        await self.db.refresh(reply)
        return reply

    async def list_replies(self, ticket_id: UUID) -> List[SupportTicketReply]:
        result = await self.db.execute(
            select(SupportTicketReply).where(SupportTicketReply.ticket_id == ticket_id)
        )
        return result.scalars().all()
