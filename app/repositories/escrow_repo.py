# app/repositories/escrow_repository.py
from typing import Optional, List

from fastapi import HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy import select
from sqlalchemy import select as sa_select
from sqlalchemy import update as sa_update
from sqlalchemy.sql import func
import uuid
from app.models.escrow import Escrow, EscrowStatus
from app.models.wallet import Wallet
from app.models.price_negotiation import PriceNegotiation


class EscrowRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, escrow_id: uuid.UUID) -> Optional[Escrow]:
        q = sa_select(Escrow).where(Escrow.id == escrow_id)
        res = await self.session.exec(q)
        return res.scalar_one_or_none()

    async def get_by_negotiation(self, negotiation_id: uuid.UUID) -> Optional[Escrow]:
        q = sa_select(Escrow).where(Escrow.payment_negotiation_id == negotiation_id)
        res = await self.session.exec(q)
        return res.scalar_one_or_none()

    async def list_for_user(self, user_id: uuid.UUID) -> List[Escrow]:
        # returns escrows where the user is payer or payee
        q = sa_select(Escrow).where(
            (Escrow.payer_wallet_id.in_(
                sa_select(Wallet.id).where(Wallet.user_id == user_id)
            )) |
            (Escrow.payee_wallet_id.in_(
                sa_select(Wallet.id).where(Wallet.user_id == user_id)
            ))
        )
        res = await self.session.exec(q)
        return res.scalars().all()

    async def create(self, escrow: Escrow) -> Escrow:
        try:
            self.session.add(escrow)
            await self.session.commit()
            await self.session.refresh(escrow)
            return escrow
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    async def create_ext(self, escrow: Escrow) -> Escrow:
        try:
            self.session.add(escrow)
            return escrow
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    async def update(self, escrow: Escrow) -> Escrow:
        self.session.add(escrow)
        await self.session.commit()
        await self.session.refresh(escrow)
        return escrow

    async def delete(self, escrow: Escrow) -> None:
        await self.session.delete(escrow)
        await self.session.commit()
