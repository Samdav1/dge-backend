import uuid
from asyncio import gather
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.price_negotiation import PriceNegotiation, NegotiationType
from app.schemas.escrow import EscrowCreate
from app.schemas.price_negotiation import PriceNegotiationCreate, PriceNegotiationUpdate
from app.repositories.price_negotiation_repo import PriceNegotiationRepository
from app.services.email_notification_service import NotificationService
from app.services.escrow_service import EscrowService
from app.schemas.user import UserRead

from app.dependencies.generator import generate_tx_ref


class PriceNegotiationService:
    def __init__(self, repo: PriceNegotiationRepository):
        self.repo = repo
        self.notification_service = NotificationService()

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

        return result