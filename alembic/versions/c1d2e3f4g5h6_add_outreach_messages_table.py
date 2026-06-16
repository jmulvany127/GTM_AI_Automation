"""add outreach_messages table

Revision ID: c1d2e3f4g5h6
Revises: a1b2c3d4e5f6
Create Date: 2026-06-16 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c1d2e3f4g5h6'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'outreach_messages',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('lead_id', sa.Integer(), nullable=False),
        sa.Column('subject', sa.String(length=500), nullable=True),
        sa.Column('email_body', sa.Text(), nullable=True),
        sa.Column('follow_up_email', sa.Text(), nullable=True),
        sa.Column('linkedin_message', sa.Text(), nullable=True),
        sa.Column('call_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['lead_id'], ['leads.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('outreach_messages')
