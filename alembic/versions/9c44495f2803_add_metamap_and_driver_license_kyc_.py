"""add_metamap_and_driver_license_kyc_columns

Revision ID: 9c44495f2803
Revises: 3d766d667485
Create Date: 2026-07-03 21:16:21.537291

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9c44495f2803'
down_revision: Union[str, None] = '3d766d667485'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add negotiated_fare to trips
    op.execute("ALTER TABLE trips ADD COLUMN IF NOT EXISTS negotiated_fare FLOAT;")
    
    # Add metamap columns to kyc
    op.execute("ALTER TABLE kyc ADD COLUMN IF NOT EXISTS metamap_verification_id VARCHAR(255);")
    op.execute("ALTER TABLE kyc ADD COLUMN IF NOT EXISTS metamap_flow_id VARCHAR(255);")
    
    # Add license columns to driver_profiles
    op.execute("ALTER TABLE driver_profiles ADD COLUMN IF NOT EXISTS license_number VARCHAR(255);")
    op.execute("ALTER TABLE driver_profiles ADD COLUMN IF NOT EXISTS license_picture_url VARCHAR(500);")
    op.execute("ALTER TABLE driver_profiles ADD COLUMN IF NOT EXISTS license_status VARCHAR(50) DEFAULT 'unverified';")
    op.execute("ALTER TABLE driver_profiles ADD COLUMN IF NOT EXISTS license_rejection_reason VARCHAR(500);")
    
    # Ensure nullable=False constraint on driver_profiles.license_status
    op.execute("UPDATE driver_profiles SET license_status = 'unverified' WHERE license_status IS NULL;")
    op.execute("ALTER TABLE driver_profiles ALTER COLUMN license_status SET NOT NULL;")


def downgrade() -> None:
    # Remove columns from driver_profiles
    op.execute("ALTER TABLE driver_profiles DROP COLUMN IF EXISTS license_rejection_reason;")
    op.execute("ALTER TABLE driver_profiles DROP COLUMN IF EXISTS license_status;")
    op.execute("ALTER TABLE driver_profiles DROP COLUMN IF EXISTS license_picture_url;")
    op.execute("ALTER TABLE driver_profiles DROP COLUMN IF EXISTS license_number;")
    
    # Remove columns from kyc
    op.execute("ALTER TABLE kyc DROP COLUMN IF EXISTS metamap_flow_id;")
    op.execute("ALTER TABLE kyc DROP COLUMN IF EXISTS metamap_verification_id;")
    
    # Remove column from trips
    op.execute("ALTER TABLE trips DROP COLUMN IF EXISTS negotiated_fare;")

