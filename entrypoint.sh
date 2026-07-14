#!/bin/sh
set -e

# Wait for Postgres (non-fatal warning on timeout)
echo "Waiting for database connection..."
python -c "
import asyncio
import sys
from app.db.session import engine

async def check():
    for i in range(15):
        try:
            async with asyncio.timeout(5.0):
                async with engine.begin() as conn:
                    pass
            print('Database is ready!')
            sys.exit(0)
        except Exception as e:
            print(f'Database not ready yet ({e})... waiting 1s')
            await asyncio.sleep(1)
    print('WARNING: Timeout waiting for database connection. Continuing anyway...')
    sys.exit(0)

asyncio.run(check())
"

# Run Alembic database migrations (non-fatal warning on error)
# If alembic_version table doesn't exist or is empty, the database was set up
# by init_db()/create_all() without Alembic tracking.
# Stamp via raw SQL (avoids full model import chain that alembic stamp triggers).
# Then skip upgrade since schema is already current.
echo "Running database migrations..."

# ALEMBIC_HEAD = latest revision ID — update this when adding new migrations
set +e
python - <<'PYEOF'
import sys, os

try:
    from sqlalchemy import create_engine, text, inspect

    ALEMBIC_HEAD = "9c44495f2803"

    db_uri = os.getenv('DB_URI', '')
    if not db_uri:
        print("WARNING: No DB_URI found, skipping migration check.")
        sys.exit(3)

    if 'asyncpg' in db_uri:
        db_uri = db_uri.replace('postgresql+asyncpg', 'postgresql+psycopg2')

    engine = create_engine(db_uri)
    with engine.connect() as conn:
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        if 'alembic_version' not in tables:
            print('No alembic_version table — creating and stamping to head via SQL...')
            conn.execute(text('CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL, CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num))'))
            conn.execute(text("INSERT INTO alembic_version (version_num) VALUES (:v)"), {'v': ALEMBIC_HEAD})
            conn.commit()
            print(f"Stamped to {ALEMBIC_HEAD}")
            sys.exit(2)  # signal: stamped, skip upgrade
        else:
            result = conn.execute(text('SELECT version_num FROM alembic_version')).fetchone()
            if result is None:
                print('alembic_version table empty — stamping to head via SQL...')
                conn.execute(text("INSERT INTO alembic_version (version_num) VALUES (:v)"), {'v': ALEMBIC_HEAD})
                conn.commit()
                print(f"Stamped to {ALEMBIC_HEAD}")
                sys.exit(2)  # signal: stamped, skip upgrade
            else:
                print(f"Alembic version found: {result[0]}")
                sys.exit(0)  # signal: run upgrade
except Exception as e:
    print(f"WARNING: Migration check failed with error: {e}")
    sys.exit(3)
PYEOF
MIGRATION_STATUS=$?
set -e

if [ "$MIGRATION_STATUS" -eq 0 ]; then
    echo "Upgrading database to latest migration..."
    alembic upgrade head || echo "WARNING: alembic upgrade head failed."
elif [ "$MIGRATION_STATUS" -eq 2 ]; then
    echo "Database stamped — skipping upgrade (schema already in sync via init_db)."
else
    echo "WARNING: Migration step skipped or failed (status $MIGRATION_STATUS)."
fi

echo "Starting Uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8001
