"""Initial migration

Revision ID: 001
Revises: 
Create Date: 2025-01-06 10:58:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create devices table
    op.create_table('devices',
        sa.Column('mac', sa.String(17), nullable=False),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('notify', sa.Boolean(), nullable=True, default=False),
        sa.Column('manufacturer', sa.String(255), nullable=True),
        sa.Column('manufacturer_status', sa.Enum('pending', 'found', 'unknown', 'error', name='manufacturerstatus'), nullable=True, default='pending'),
        sa.Column('manufacturer_last_attempt', sa.DateTime(), nullable=True),
        sa.Column('first_seen', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('last_seen', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('mac')
    )

def downgrade() -> None:
    op.drop_table('devices')
