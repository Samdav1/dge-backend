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

    async def list_tickets(self, user_id: Optional[UUID] = None, is_admin: bool = False) -> List[dict]:
        from app.models.user import Users
        from app.models.admin import SuperAdmin
        from app.models.profile import Profile

        query = (
            select(SupportTicket, Users.username, Users.email, Profile.first_name, Profile.last_name, SuperAdmin.name)
            .outerjoin(Users, SupportTicket.user_id == Users.id)
            .outerjoin(Profile, Users.id == Profile.user_id)
            .outerjoin(SuperAdmin, SupportTicket.assigned_admin_id == SuperAdmin.id)
        )
        if not is_admin and user_id:
            query = query.where(SupportTicket.user_id == user_id)

        query = query.order_by(SupportTicket.created_at.desc())
        result = await self.db.execute(query)
        tickets = []
        for ticket, username, email, first_name, last_name, admin_name in result.all():
            ticket_dict = ticket.model_dump()
            full_name = f"{first_name} {last_name}".strip() if (first_name or last_name) else None
            ticket_dict["user_name"] = full_name or username or email or admin_name or "User"
            ticket_dict["user_email"] = email
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
        from app.models.profile import Profile
        result = await self.db.execute(
            select(SupportTicketReply, Users.username, Users.email, Profile.first_name, Profile.last_name, SuperAdmin.name)
            .outerjoin(Users, SupportTicketReply.author_user_id == Users.id)
            .outerjoin(Profile, Users.id == Profile.user_id)
            .outerjoin(SuperAdmin, SupportTicketReply.author_admin_id == SuperAdmin.id)
            .where(SupportTicketReply.ticket_id == ticket_id)
            .order_by(SupportTicketReply.created_at.asc())
        )
        replies = []
        for reply, username, email, first_name, last_name, admin_name in result.all():
            reply_dict = reply.model_dump()
            full_name = f"{first_name} {last_name}".strip() if (first_name or last_name) else None
            reply_dict["author_name"] = full_name or username or admin_name or email or "Support Team"
            replies.append(reply_dict)
        return replies

