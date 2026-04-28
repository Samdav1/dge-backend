from fastapi import HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from typing import List, Optional
import uuid

from app.models import Users
from app.models.price_negotiation import PriceNegotiation
from app.schemas.price_negotiation import PriceNegotiationRead, NegotiationType

class PriceNegotiationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, negotiation: PriceNegotiation) -> PriceNegotiation:
        self.db.add(negotiation)
        await self.db.commit()
        await self.db.refresh(negotiation)
        return negotiation

    async def get_by_id(self, negotiation_id: uuid.UUID) -> Optional[PriceNegotiation]:
        result = await self.db.execute(select(PriceNegotiation).where(PriceNegotiation.id == negotiation_id))
        return result.scalar_one_or_none()

    async def get_for_user(self, user_id: uuid.UUID) -> List[PriceNegotiationRead]:
        """
        Fetches all price negotiations for a user, dynamically setting the
        negotiation type based on the user's role.
        """
        query = select(PriceNegotiation).where(
            (PriceNegotiation.initiator_id == user_id) |
            (PriceNegotiation.receiver_id == user_id)
        )
        result = await self.db.execute(query)
        db_negotiations = result.scalars().all()

        response_schemas = []
        for db_obj in db_negotiations:
            schema = PriceNegotiationRead.model_validate(db_obj)
            if db_obj.receiver_id == user_id:
                schema.negotiation_type = NegotiationType.incoming
            response_schemas.append(schema)

        return response_schemas

    async def update(self, negotiation: PriceNegotiation, updates: dict) -> PriceNegotiation:
        for key, value in updates.items():
            setattr(negotiation, key, value)
        await self.db.commit()
        await self.db.refresh(negotiation)
        return negotiation

    async def get_user_by_id(self, user_id):
        stmt = select(Users).where(Users.id == user_id)
        result = await self.db.exec(stmt)
        user = result.first()
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        return user
