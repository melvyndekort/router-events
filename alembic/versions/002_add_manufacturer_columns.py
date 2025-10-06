"""Add manufacturer columns

Revision ID: 002
Revises: 001
Create Date: 2025-01-06 11:07:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Add manufacturer columns to existing devices table
    try:
        op.add_column('devices', sa.Column('manufacturer', sa.String(255), nullable=True))
    except Exception:
        pass  # Column already exists
    
    try:
        op.add_column('devices', sa.Column('manufacturer_status', 
            sa.Enum('pending', 'found', 'unknown', 'error', name='manufacturerstatus'), 
            nullable=True, default='pending'))
    except Exception:
        pass  # Column already exists
    
    try:
        op.add_column('devices', sa.Column('manufacturer_last_attempt', sa.DateTime(), nullable=True))
    except Exception:
        pass  # Column already exists

def downgrade() -> None:
    op.drop_column('devices', 'manufacturer_last_attempt')
    op.drop_column('devices', 'manufacturer_status')
    op.drop_column('devices', 'manufacturer')
