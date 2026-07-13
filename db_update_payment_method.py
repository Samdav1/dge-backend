import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.config import settings

engine = create_async_engine(settings.database_uri, execution_options={"isolation_level": "AUTOCOMMIT"})

async def run_update():
    async with engine.begin() as conn:
        print("Starting DB schema updates for payment_method...")
        try:
            await conn.execute(text("ALTER TABLE price_negotiations ADD COLUMN IF NOT EXISTS payment_method VARCHAR DEFAULT 'platform';"))
            print("Added payment_method column to price_negotiations table.")
        except Exception as e:
            print("Error altering price_negotiations table:", e)

        try:
            await conn.execute(text("ALTER TABLE escrow ADD COLUMN IF NOT EXISTS payment_method VARCHAR DEFAULT 'platform';"))
            print("Added payment_method column to escrow table.")
        except Exception as e:
            print("Error altering escrow table:", e)
            
        print("Done.")

async def main():
    await run_update()

if __name__ == "__main__":
    asyncio.run(main())
