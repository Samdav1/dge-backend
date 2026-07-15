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


def downgrade() -> None:
    # Remove vehicle_type from trips table
    op.execute("ALTER TABLE trips DROP COLUMN IF EXISTS vehicle_type;")
    
    # Remove payment_method from escrow table
    op.execute("ALTER TABLE escrow DROP COLUMN IF EXISTS payment_method;")

