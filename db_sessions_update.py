import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.config import settings

engine = create_async_engine(settings.database_uri, execution_options={"isolation_level": "AUTOCOMMIT"})

async def run_update():
    async with engine.begin() as conn:
        print("Starting DB schema updates...")
        
        try:
            await conn.execute(text("CREATE TYPE adminsessionstatus AS ENUM ('CURRENT', 'ACTIVE', 'EXPIRED', 'REVOKED');"))
            print("Created adminsessionstatus enum.")
        except Exception as e:
            print("Enum adminsessionstatus might already exist or error:", e)

        try:
            await conn.execute(text("ALTER TABLE superadmin ADD COLUMN email_notifs BOOLEAN DEFAULT TRUE NOT NULL;"))
            await conn.execute(text("ALTER TABLE superadmin ADD COLUMN push_notifs BOOLEAN DEFAULT TRUE NOT NULL;"))
            await conn.execute(text("ALTER TABLE superadmin ADD COLUMN security_alerts BOOLEAN DEFAULT FALSE NOT NULL;"))
            print("Added notification preference columns to superadmin.")
        except Exception as e:
            print("Notification columns might already exist or error:", e)

        try:
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS admin_sessions (
                    id UUID PRIMARY KEY,
                    admin_id UUID NOT NULL REFERENCES superadmin(id),
                    device VARCHAR NOT NULL,
                    location VARCHAR,
                    ip_address VARCHAR NOT NULL,
                    status adminsessionstatus DEFAULT 'CURRENT' NOT NULL,
                    last_activity TIMESTAMP WITH TIME ZONE NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL
                );
            """))
            print("Created admin_sessions table.")
        except Exception as e:
            print("admin_sessions table error:", e)
            
        print("Done.")

asyncio.run(run_update())
