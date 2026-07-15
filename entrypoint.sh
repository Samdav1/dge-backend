#!/bin/sh
set -e

# Wait for Postgres (non-fatal warning on timeout)
echo "Waiting for database connection..."
python -c "
import asyncio
import sys

async def check():
    for i in range(15):
        try:
            from app.db.session import engine
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
# Inspect database schema to self-heal and stamp the database to the correct version matching existing tables/columns
# This ensures that any missing/outdated columns are correctly upgraded on deploy.
echo "Running database migrations..."

set +e
python - <<'PYEOF'
import sys, os

try:
    from sqlalchemy import create_engine, text, inspect

    db_uri = os.getenv('DB_URI', '')
    if not db_uri:
        print("WARNING: No DB_URI found, skipping migration check.")
        sys.exit(3)

    if 'asyncpg' in db_uri:
        db_uri = db_uri.replace('postgresql+asyncpg', 'postgresql+psycopg2')

    engine = create_engine(db_uri)
    with engine.connect() as conn:
        inspector = inspect(engine)
        table_names = inspector.get_table_names()
        
        # Define check functions for migrations in reverse chronological order
        migrations = [
            ("a966bdf0ab3c", lambda insp: "escrow" in table_names and "payment_method" in [c["name"] for c in insp.get_columns("escrow")]),
            ("9c44495f2803", lambda insp: "users" in table_names and "identity_verified" in [c["name"] for c in insp.get_columns("users")]),
            ("3d766d667485", lambda insp: "driver_vehicles" in table_names),
            ("0c6aa91a55ea", lambda insp: "escrow" in table_names and "platform_fee_percent" in [c["name"] for c in insp.get_columns("escrow")]),
            ("b0dfd279c5fe", lambda insp: "monnify_payments" in table_names),
            ("e6a0809d47fe", lambda insp: "posted_jobs" in table_names),
            ("76025a38eaa0", lambda insp: "escrow" in table_names and "duration_seconds" in [c["name"] for c in insp.get_columns("escrow")]),
            ("a66c9cf4f6c7", lambda insp: "users" in table_names and "plate_number" in [c["name"] for c in insp.get_columns("users")]),
            ("fa8ba665d169", lambda insp: "user_portfolio" in table_names and "rate" in [c["name"] for c in insp.get_columns("user_portfolio")]),
            ("3940ece90f16", lambda insp: "kyc" in table_names and "value" in [c["name"] for c in insp.get_columns("kyc")]),
            ("56c17be756f6", lambda insp: "users" in table_names and "google_id" in [c["name"] for c in insp.get_columns("users")]),
            ("25416e912c15", lambda insp: "users" in table_names and "avatar" in [c["name"] for c in insp.get_columns("users")]),
            ("260b77f76526", lambda insp: "services" in table_names and "price" in [c["name"] for c in insp.get_columns("services")]),
            ("c782e9c35d27", lambda insp: "users" in table_names and "is_verified" in [c["name"] for c in insp.get_columns("users")]),
            ("ab861dc01771", lambda insp: "transactions" in table_names and "users_id" in [c["name"] for c in insp.get_columns("transactions")]),
        ]

        # Determine actual database schema revision
        detected_rev = None
        for rev, check_fn in migrations:
            try:
                if check_fn(inspector):
                    detected_rev = rev
                    break
            except Exception:
                pass

        # Check existing alembic_version table
        has_alembic_table = "alembic_version" in table_names
        current_rev = None
        if has_alembic_table:
            res = conn.execute(text("SELECT version_num FROM alembic_version")).fetchone()
            if res:
                current_rev = res[0]

        print(f"Self-healing check: detected_rev={detected_rev}, current_rev={current_rev}")

        if detected_rev != current_rev:
            print(f"Updating database alembic_version from {current_rev} to {detected_rev}...")
            if not has_alembic_table:
                conn.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL, CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num))"))
                conn.commit()
            
            conn.execute(text("DELETE FROM alembic_version"))
            if detected_rev:
                conn.execute(text("INSERT INTO alembic_version (version_num) VALUES (:v)"), {"v": detected_rev})
            conn.commit()
            print("Successfully updated database stamp to match detected state!")
        
        sys.exit(0) # Signal: run upgrade
except Exception as e:
    print(f"WARNING: Self-healing database check failed with error: {e}")
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
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
