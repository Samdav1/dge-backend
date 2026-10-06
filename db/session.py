import logging
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from app.config import settings

logger = logging.getLogger(__name__)

engine = None
if settings.database_uri:
    engine = create_async_engine(
        settings.database_uri,
        echo=True,
        future=True,
        pool_size=20,
        max_overflow=10
    )
else:
    logger.error("❌ DB_URI environment variable is not configured or empty!")

async def get_session() -> AsyncSession:
    if engine is None:
        raise RuntimeError("Database engine is not initialized. Please configure DB_URI.")
    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session


async def init_db():
    if engine is None:
        logger.error("Skipping init_db() because database engine is not initialized.")
        return
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)