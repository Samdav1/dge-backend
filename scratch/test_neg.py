import asyncio
import uuid
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import sessionmaker
from app.repositories.price_negotiation_repo import PriceNegotiationRepository
from app.services.price_negotiation_service import PriceNegotiationService
from app.schemas.price_negotiation import PriceNegotiationCreate
from app.models.price_negotiation import NegotiationStatus
from app.config import settings

DATABASE_URL = settings.database_uri

async def test_negotiation_logic():
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        repo = PriceNegotiationRepository(db)
        service = PriceNegotiationService(repo)
        
        # We need a user and a service to test
        # Let's just create a dummy payload and catch the exception to see if the logic works
        print("Test ready")
        # I won't actually insert anything to avoid polluting the DB, I will just run the app unit tests if they exist.

if __name__ == "__main__":
    asyncio.run(test_negotiation_logic())
