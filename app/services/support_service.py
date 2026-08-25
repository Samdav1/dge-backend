import os
from typing import List, Optional
from uuid import UUID
from sqlmodel.ext.asyncio.session import AsyncSession
from app.models.support_ticket import SupportTicket, SupportTicketReply
from app.repositories.support_repo import SupportTicketRepository
from app.services.email_notification_service import NotificationService


class SupportTicketService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = SupportTicketRepository(db)
        self.notifier = NotificationService()

    # --- Tickets ---
    async def create_ticket(self, payload: dict, user = None) -> SupportTicket:
        ticket = SupportTicket(**payload)
        created_ticket = await self.repo.create_ticket(ticket)
        
        if user:
            try:
                self.notifier.send_ticket_created_mail(user, created_ticket)
            except Exception as e:
                print(f"Error dispatching ticket creation email: {e}")

        return created_ticket

    async def get_ticket(self, ticket_id: UUID) -> SupportTicket:
        ticket = await self.repo.get_ticket(ticket_id)
        if not ticket:
            raise ValueError("Ticket not found")
        return ticket

    async def list_tickets(self, user_id: Optional[UUID] = None, is_admin: bool = False) -> List[dict]:
        return await self.repo.list_tickets(user_id=user_id, is_admin=is_admin)

    async def update_ticket(self, ticket_id: UUID, payload: dict) -> SupportTicket:
        ticket = await self.get_ticket(ticket_id)
        return await self.repo.update_ticket(ticket, payload)

    async def delete_ticket(self, ticket_id: UUID) -> None:
        ticket = await self.get_ticket(ticket_id)
        await self.repo.delete_ticket(ticket)

    # --- Replies ---
    async def create_reply(self, payload: dict, current_user = None) -> SupportTicketReply:
        reply_obj = SupportTicketReply(**payload)
        reply = await self.repo.create_reply(reply_obj)

        try:
            ticket = await self.get_ticket(reply.ticket_id)
            if ticket:
                is_admin_reply = bool(reply.author_admin_id or (current_user and getattr(current_user, 'is_admin', False)))
                author_name = getattr(current_user, 'username', None) if current_user else None
                if not author_name:
                    author_name = "Support Agent" if is_admin_reply else "User"

                if is_admin_reply:
                    from app.models.user import Users
                    creator = await self.db.get(Users, ticket.user_id)
                    if creator and creator.email:
                        self.notifier.send_ticket_reply_mail(
                            recipient_email=creator.email,
                            recipient_name=creator.username,
                            ticket=ticket,
                            reply_message=reply.message,
                            author_name=author_name,
                            is_admin_reply=True
                        )
                else:
                    admin_email = os.getenv("SUPPORT_ADMIN_EMAIL") or os.getenv("EMAIL_SENDER_ADDRESS")
                    if admin_email:
                        self.notifier.send_ticket_reply_mail(
                            recipient_email=admin_email,
                            recipient_name="Support Admin",
                            ticket=ticket,
                            reply_message=reply.message,
                            author_name=author_name,
                            is_admin_reply=False
                        )
        except Exception as e:
            print(f"Error dispatching ticket reply email: {e}")

        return reply

    async def list_replies(self, ticket_id: UUID) -> List[dict]:
        return await self.repo.list_replies(ticket_id)
