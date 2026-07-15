"""add_escrow_payment_method_and_trip_vehicle_type

Revision ID: a966bdf0ab3c
Revises: 9c44495f2803
Create Date: 2026-07-15 18:26:07.628217

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a966bdf0ab3c'
down_revision: Union[str, None] = '9c44495f2803'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add payment_method to escrow table
    op.execute("ALTER TABLE escrow ADD COLUMN IF NOT EXISTS payment_method TEXT DEFAULT 'platform';")
    
    # Add vehicle_type to trips table
    op.execute("ALTER TABLE trips ADD COLUMN IF NOT EXISTS vehicle_type VARCHAR(50) DEFAULT 'car';")
    op.execute("UPDATE trips SET vehicle_type = 'car' WHERE vehicle_type IS NULL;")
    op.execute("ALTER TABLE trips ALTER COLUMN vehicle_type SET NOT NULL;")

    # Add payment_method to price_negotiations table
    op.execute("ALTER TABLE price_negotiations ADD COLUMN IF NOT EXISTS payment_method TEXT DEFAULT 'platform';")
    
    # Add vehicle_type to driver_profiles table
    op.execute("ALTER TABLE driver_profiles ADD COLUMN IF NOT EXISTS vehicle_type VARCHAR(50) DEFAULT 'car';")
    op.execute("UPDATE driver_profiles SET vehicle_type = 'car' WHERE vehicle_type IS NULL;")
    op.execute("ALTER TABLE driver_profiles ALTER COLUMN vehicle_type SET NOT NULL;")

    # Add payment_method to posted_jobs table
    op.execute("ALTER TABLE posted_jobs ADD COLUMN IF NOT EXISTS payment_method VARCHAR(50) DEFAULT 'platform';")
    op.execute("UPDATE posted_jobs SET payment_method = 'platform' WHERE payment_method IS NULL;")
    op.execute("ALTER TABLE posted_jobs ALTER COLUMN payment_method SET NOT NULL;")


def downgrade() -> None:
    # Remove columns from posted_jobs
    op.execute("ALTER TABLE posted_jobs DROP COLUMN IF EXISTS payment_method;")

    # Remove columns from driver_profiles
    op.execute("ALTER TABLE driver_profiles DROP COLUMN IF EXISTS vehicle_type;")

    # Remove columns from price_negotiations
    op.execute("ALTER TABLE price_negotiations DROP COLUMN IF EXISTS payment_method;")

    # Remove vehicle_type from trips table
    op.execute("ALTER TABLE trips DROP COLUMN IF EXISTS vehicle_type;")
    
    # Remove payment_method from escrow table
    op.execute("ALTER TABLE escrow DROP COLUMN IF EXISTS payment_method;")


