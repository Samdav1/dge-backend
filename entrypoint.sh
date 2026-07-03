#!/bin/sh
set -e

# Wait for Postgres
echo "Waiting for database connection..."
python -c "
import asyncio
import sys
from app.db.session import engine

async def check():
    for i in range(30):
        try:
            async with asyncio.timeout(5.0):
                async with engine.begin() as conn:
                    pass
            print('Database is ready!')
            sys.exit(0)
        except Exception as e:
            print(f'Database not ready yet ({e})... waiting 1s')
            await asyncio.sleep(1)
    print('Timeout waiting for database')
    sys.exit(1)

asyncio.run(check())
"
# Seed service categories
echo "Seeding service categories..."
python seed_categories.py

# Run Alembic database migrations
echo "Running database migrations..."
alembic upgrade head

echo "Starting Uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
