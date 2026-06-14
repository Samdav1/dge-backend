from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from app.config import settings

engine = create_async_engine(
    settings.database_uri,
    echo=True,
    future=True,
    pool_size=20,
    max_overflow=10
)

async def get_session() -> AsyncSession:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
        from sqlalchemy import text
        try:
            await conn.execute(text("ALTER TABLE trips ADD COLUMN IF NOT EXISTS negotiated_fare FLOAT;"))
        except Exception as e:
            print(f"Skipping column migration check: {e}")