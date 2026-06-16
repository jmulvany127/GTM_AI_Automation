"""add lead_analysis table

Revision ID: a1b2c3d4e5f6
Revises: b1c2d3e4f5g6
Create Date: 2026-06-16 12:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'b1c2d3e4f5g6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'lead_analysis',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('lead_id', sa.Integer(), nullable=False),
        sa.Column('company_summary', sa.Text(), nullable=True),
        sa.Column('persona_type', sa.String(length=100), nullable=True),
        sa.Column('pain_points', sa.Text(), nullable=True),
        sa.Column('buying_signals', sa.Text(), nullable=True),
        sa.Column('objections', sa.Text(), nullable=True),
        sa.Column('fit_score', sa.Integer(), nullable=True),
        sa.Column('urgency_score', sa.Integer(), nullable=True),
        sa.Column('overall_score', sa.Integer(), nullable=True),
        sa.Column('recommended_action', sa.Text(), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('raw_ai_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['lead_id'], ['leads.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('lead_analysis')
