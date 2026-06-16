"""add automation_metrics table

Revision ID: d1e2f3g4h5i6
Revises: c1d2e3f4g5h6
Create Date: 2026-06-16 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd1e2f3g4h5i6'
down_revision: Union[str, Sequence[str], None] = 'c1d2e3f4g5h6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'automation_metrics',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('lead_id', sa.Integer(), nullable=False),
        sa.Column('workflow_name', sa.String(length=100), server_default='gtm_workflow', nullable=False),
        sa.Column('actions_executed', sa.Text(), nullable=True),
        sa.Column('requires_human_review', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('reasoning_summary', sa.Text(), nullable=True),
        sa.Column('manual_time_estimate_minutes', sa.Integer(), server_default='25', nullable=False),
        sa.Column('automated_time_seconds', sa.Float(), nullable=True),
        sa.Column('estimated_time_saved_minutes', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['lead_id'], ['leads.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('automation_metrics')
