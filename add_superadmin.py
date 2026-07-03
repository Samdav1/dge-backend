import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.config import settings

engine = create_async_engine(settings.database_uri, execution_options={"isolation_level": "AUTOCOMMIT"})

async def add_admin():
    async with engine.begin() as conn:
        print("Adding superadmin...")
        sql = """
        INSERT INTO "public"."superadmin" ("id","name","email","phone_number","hashed_password","rank","status","is_active","email_verified","phone_verified","mfa_enabled","mfa_secret","created_at","updated_at","last_login_at","avatar","updated_by","email_notifs","push_notifs","security_alerts")
        VALUES ('5a26c322-237e-4538-af48-d1cc7ea1748c','Samuel','admin@dge.com',NULL,'$pbkdf2-sha256$29000$cS5FaE3pHcM4B8AYo7T2vg$JJZtJyqMvZNk55pTuuifHg5NiGvwpLL6HtoerC32Ysw','Super','Pending',TRUE,TRUE,TRUE,TRUE,'','2026-05-04 13:49:09.532022+01','2026-05-04 13:49:09.532022+01','2026-05-04 13:49:09.532022+01','',NULL,TRUE,TRUE,TRUE)
        ON CONFLICT (id) DO NOTHING;
        """
        try:
            await conn.execute(text(sql))
            print("Superadmin added successfully!")
        except Exception as e:
            print("Error adding superadmin:", e)

if __name__ == "__main__":
    asyncio.run(add_admin())
