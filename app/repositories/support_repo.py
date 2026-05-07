from typing import List, Optional
from uuid import UUID
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from datetime import datetime, timezone
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

    async def list_tickets(self) -> List[dict]:
        from app.models.user import Users
        from app.models.admin import SuperAdmin
        result = await self.db.execute(
            select(SupportTicket, Users.username, SuperAdmin.name)
            .outerjoin(Users, SupportTicket.user_id == Users.id)
            .outerjoin(SuperAdmin, SupportTicket.assigned_admin_id == SuperAdmin.id)
        )
        tickets = []
        for ticket, username, admin_name in result.all():
            ticket_dict = ticket.model_dump()
            ticket_dict["user_name"] = username or admin_name or "Unknown"
            tickets.append(ticket_dict)
        return tickets

    async def update_ticket(self, ticket: SupportTicket, data: dict) -> SupportTicket:
        for key, value in data.items():
            setattr(ticket, key, value)
        ticket.updated_at = datetime.now(timezone.utc)
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

    async def list_replies(self, ticket_id: UUID) -> List[dict]:
        from app.models.user import Users
        from app.models.admin import SuperAdmin
        result = await self.db.execute(
            select(SupportTicketReply, Users.username, SuperAdmin.name)
            .outerjoin(Users, SupportTicketReply.author_user_id == Users.id)
            .outerjoin(SuperAdmin, SupportTicketReply.author_admin_id == SuperAdmin.id)
            .where(SupportTicketReply.ticket_id == ticket_id)
        )
        replies = []
        for reply, username, admin_name in result.all():
            reply_dict = reply.model_dump()
            reply_dict["author_name"] = username or admin_name or "Support Team"
            replies.append(reply_dict)
        return replies
