"""add caption to post

Revision ID: c5f1a3b2e8d9
Revises: b3e9f2a1c4d7
Create Date: 2026-03-31 00:00:00.000000

Adds:
  post : caption  VARCHAR  NULLABLE  — optional caption text for the post
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c5f1a3b2e8d9'
down_revision: Union[str, Sequence[str], None] = 'b3e9f2a1c4d7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'post',
        sa.Column('caption', sa.String(length=500), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('post', 'caption')
