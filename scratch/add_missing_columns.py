import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import os
from dotenv import load_dotenv

load_dotenv()

DB_URI = os.getenv("DB_URI")

async def main():
    if not DB_URI:
        print("DB_URI not found in env")
        return
    
    print(f"Connecting to database: {DB_URI}")
    engine = create_async_engine(DB_URI)
    
    async with engine.begin() as conn:
        print("Adding columns to price_negotiations table...")
        try:
            await conn.execute(text("ALTER TABLE price_negotiations ADD COLUMN IF NOT EXISTS payment_method TEXT DEFAULT 'platform';"))
            print("Successfully added payment_method")
        except Exception as e:
            print(f"Error adding payment_method: {e}")
            
        try:
            await conn.execute(text("ALTER TABLE price_negotiations ADD COLUMN IF NOT EXISTS posted_job_id UUID REFERENCES posted_jobs(id);"))
            print("Successfully added posted_job_id")
        except Exception as e:
            print(f"Error adding posted_job_id: {e}")
            
    print("Done!")

if __name__ == "__main__":
    asyncio.run(main())
