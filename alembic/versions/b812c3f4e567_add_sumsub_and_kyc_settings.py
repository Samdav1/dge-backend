"""add_sumsub_and_kyc_settings

Revision ID: b812c3f4e567
Revises: a966bdf0ab3c
Create Date: 2026-08-06 05:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b812c3f4e567'
down_revision: Union[str, None] = 'a966bdf0ab3c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add Sumsub fields and kyc_provider to kyc table
    op.execute("ALTER TABLE kyc ADD COLUMN IF NOT EXISTS sumsub_applicant_id VARCHAR(255);")
    op.execute("ALTER TABLE kyc ADD COLUMN IF NOT EXISTS sumsub_inspection_id VARCHAR(255);")
    op.execute("ALTER TABLE kyc ADD COLUMN IF NOT EXISTS kyc_provider VARCHAR(50) DEFAULT 'sumsub';")

    # Create admin_kyc_settings table
    op.execute("""
    CREATE TABLE IF NOT EXISTS admin_kyc_settings (
        id INT PRIMARY KEY DEFAULT 1,
        active_provider VARCHAR(50) NOT NULL DEFAULT 'sumsub',
        updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
        updated_by_admin_id UUID REFERENCES superadmin(id) ON DELETE SET NULL
    );
    """)

    # Seed default row id=1 if not exists
    op.execute("""
    INSERT INTO admin_kyc_settings (id, active_provider, updated_at)
    VALUES (1, 'sumsub', NOW())
    ON CONFLICT (id) DO NOTHING;
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS admin_kyc_settings;")
    op.execute("ALTER TABLE kyc DROP COLUMN IF EXISTS kyc_provider;")
    op.execute("ALTER TABLE kyc DROP COLUMN IF EXISTS sumsub_inspection_id;")
    op.execute("ALTER TABLE kyc DROP COLUMN IF EXISTS sumsub_applicant_id;")
