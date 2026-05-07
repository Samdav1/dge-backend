import uuid
from asyncio import gather
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.price_negotiation import PriceNegotiation, NegotiationType
from app.schemas.escrow import EscrowCreate
from app.schemas.price_negotiation import PriceNegotiationCreate, PriceNegotiationUpdate
from app.repositories.price_negotiation_repo import PriceNegotiationRepository
from app.services.email_notification_service import NotificationService as EmailNotificationService
from app.services.escrow_service import EscrowService
from app.schemas.user import UserRead

from app.dependencies.generator import generate_tx_ref

from app.services.notifications_service import NotificationService as InAppNotificationService
from app.repositories.notifications_repo import NotificationRepository
from app.schemas.notifications import NotificationCreate
from app.models.notifications import NotificationType
from app.websocket_endpoints.chat_ws import manager


class PriceNegotiationService:
    def __init__(self, repo: PriceNegotiationRepository):
        self.repo = repo
        self.notification_service = EmailNotificationService()

    async def create(self, payload: PriceNegotiationCreate, initiator_id: uuid.UUID) -> PriceNegotiation:
        negotiation_data = PriceNegotiation(
            service_id=payload.service_id,
            initiator_id=initiator_id,
            receiver_id=payload.receiver_id,
            negotiation_type=NegotiationType.outgoing,
            proposed_price_cents=payload.proposed_price_cents,
            message=payload.message,
        )

        created_negotiation = await self.repo.create(negotiation_data)

        receiver, initiator = await gather(
            self.repo.get_user_by_id(payload.receiver_id),
            self.repo.get_user_by_id(initiator_id)
        )

        self.notification_service.send_price_negotiation_offer(
            receiver=receiver,
            initiator=initiator,
            negotiation=created_negotiation
        )

        in_app_service = InAppNotificationService(NotificationRepository(self.repo.db))
        notification_data = NotificationCreate(
            user_id=payload.receiver_id,
            price_negotiation_id=created_negotiation.id,
            type=NotificationType.general,
            message=f"You have received a new price negotiation offer for ${payload.proposed_price_cents / 100:.2f}.",
            metadataInfo={"negotiation_id": str(created_negotiation.id)}
        )
        notif = await in_app_service.create_notification(notification_data, initiator_id)

        await manager.send_to_user(str(payload.receiver_id), {
            "action": "notification",
            "notification": {
                "id": str(notif.id),
                "type": notif.type.value,
                "message": notif.message,
                "created_at": notif.created_at.isoformat()
            }
        })
        await manager.send_to_user(str(payload.receiver_id), {
            "action": "negotiation_updated",
            "negotiation_id": str(created_negotiation.id)
        })

        return created_negotiation

    async def get_for_user(self, user_id: uuid.UUID):
        return await self.repo.get_for_user(user_id)

    async def update(self, negotiation_id: uuid.UUID, payload: PriceNegotiationUpdate, db: AsyncSession,
                     user: UserRead):
        negotiation = await self.repo.get_by_id(negotiation_id)
        if not negotiation:
            raise ValueError("Negotiation not found")

        result = await self.repo.update(negotiation, payload.dict(exclude_unset=True))

        if payload.status == "accepted":
            escrow_service = EscrowService(db)

            # Use the generator function here
            tx_reference = generate_tx_ref(prefix="ESCROW")

            new_escrow = EscrowCreate(
                payment_negotiation_id=negotiation_id,
                amount_cents=negotiation.proposed_price_cents,  # Use the agreed price from negotiation
                reference=tx_reference,
            )
            await escrow_service.create_escrow(user=user, payload=new_escrow)

        if payload.status:
            if payload.status == "accepted":
                notif_type = NotificationType.offer_accepted
                msg = "Your price negotiation was accepted."
            elif payload.status == "rejected":
                notif_type = NotificationType.offer_rejected
                msg = "Your price negotiation was rejected."
            elif payload.status == "countered":
                notif_type = NotificationType.general
                msg = f"You received a counter offer for ${payload.proposed_price_cents / 100:.2f}." if payload.proposed_price_cents else "You received a counter offer."
            else:
                notif_type = NotificationType.general
                msg = "Your price negotiation was updated."

            target_user_id = negotiation.initiator_id if user.id == negotiation.receiver_id else negotiation.receiver_id

            in_app_service = InAppNotificationService(NotificationRepository(db))
            notification_data = NotificationCreate(
                user_id=target_user_id,
                price_negotiation_id=negotiation.id,
                type=notif_type,
                message=msg,
                metadataInfo={"negotiation_id": str(negotiation.id)}
            )
            notif = await in_app_service.create_notification(notification_data, user.id)

            await manager.send_to_user(str(target_user_id), {
                "action": "notification",
                "notification": {
                    "id": str(notif.id),
                    "type": notif.type.value,
                    "message": notif.message,
                    "created_at": notif.created_at.isoformat()
                }
            })
            await manager.send_to_user(str(target_user_id), {
                "action": "negotiation_updated",
                "negotiation_id": str(negotiation.id)
            })

        return result