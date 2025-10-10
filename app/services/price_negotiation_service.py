import uuid
from app.models.price_negotiation import PriceNegotiation, NegotiationType
from ..schemas.price_negotiation import PriceNegotiationCreate, PriceNegotiationUpdate
from app.repositories.price_negotiation_repo import PriceNegotiationRepository


class PriceNegotiationService:
    def __init__(self, repo: PriceNegotiationRepository):
        self.repo = repo

    async def create(self, payload: PriceNegotiationCreate, initiator_id: uuid.UUID) -> PriceNegotiation:
        negotiation = PriceNegotiation(
            service_id=payload.service_id,
            initiator_id=initiator_id,
            receiver_id=payload.receiver_id,
            negotiation_type=NegotiationType.outgoing,
            proposed_price_cents=payload.proposed_price_cents,
            message=payload.message,
        )
        return await self.repo.create(negotiation)

    async def get_for_user(self, user_id: uuid.UUID):
        return await self.repo.get_for_user(user_id)

    async def update(self, negotiation_id: uuid.UUID, payload: PriceNegotiationUpdate):
        negotiation = await self.repo.get_by_id(negotiation_id)
        if not negotiation:
            raise ValueError("Negotiation not found")
        return await self.repo.update(negotiation, payload.dict(exclude_unset=True))
