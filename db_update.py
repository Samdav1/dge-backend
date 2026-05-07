import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.config import settings

engine = create_async_engine(settings.database_uri, execution_options={"isolation_level": "AUTOCOMMIT"})

async def run_update():
    async with engine.begin() as conn:
        print("Starting DB schema updates...")
        try:
            await conn.execute(text("CREATE TYPE rolestatus AS ENUM ('ACTIVE', 'DEACTIVATED');"))
            print("Created rolestatus enum.")
        except Exception as e:
            print("Enum might already exist or error:", e)

        try:
            await conn.execute(text("ALTER TABLE roles ADD COLUMN description VARCHAR;"))
            await conn.execute(text("ALTER TABLE roles ADD COLUMN status rolestatus DEFAULT 'ACTIVE';"))
            print("Added description and status to roles.")
        except Exception as e:
            print("Columns might already exist or error:", e)

        try:
            await conn.execute(text("ALTER TABLE roles DROP COLUMN team_user_id;"))
            print("Dropped team_user_id from roles.")
        except Exception as e:
            print("Column team_user_id might already be dropped or error:", e)

        try:
            await conn.execute(text("ALTER TABLE teamusers ADD COLUMN role_id UUID REFERENCES roles(id);"))
            print("Added role_id to teamusers.")
        except Exception as e:
            print("Column role_id might already exist or error:", e)
            
        print("Done.")

asyncio.run(run_update())
