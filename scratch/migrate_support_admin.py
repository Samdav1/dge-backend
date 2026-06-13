import asyncio
from sqlmodel import text
from app.db.session import engine

async def run_migration():
    async with engine.begin() as conn:
        try:
            await conn.execute(text('ALTER TABLE support_ticket_replies ADD COLUMN author_admin_id UUID REFERENCES superadmin(id)'))
            print("Successfully added author_admin_id column")
        except Exception as e:
            print(f"Error adding column: {e}")
            
        try:
            await conn.execute(text('ALTER TABLE support_tickets ADD COLUMN assigned_admin_id UUID REFERENCES superadmin(id)'))
            print("Successfully added assigned_admin_id column")
        except Exception as e:
            print(f"Error adding column: {e}")

if __name__ == "__main__":
    asyncio.run(run_migration())
