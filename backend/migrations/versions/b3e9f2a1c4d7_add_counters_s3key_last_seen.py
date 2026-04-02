"""add vote counters, s3_key, last_seen_at

Revision ID: b3e9f2a1c4d7
Revises: e4cc454ed4ba
Create Date: 2026-03-31 00:00:00.000000

Adds:
  fb_user   : last_seen_at  TIMESTAMP   — when the user last authenticated
  photo     : s3_key        VARCHAR     UNIQUE  — stable S3 object key (unique photo marker)
  photo     : vote_count    INTEGER     DEFAULT 0  — denormalised per-photo vote counter
  post      : total_votes   INTEGER     DEFAULT 0  — denormalised total votes counter

Also adds voted_at column to vote table (renamed from created_at semantically via new column;
old created_at is preserved for backward compatibility).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b3e9f2a1c4d7'
down_revision: Union[str, Sequence[str], None] = 'e4cc454ed4ba'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    # ── fb_user: last_seen_at ────────────────────────────────────────────────
    op.add_column(
        'fb_user',
        sa.Column('last_seen_at', sa.DateTime(), nullable=True)
    )

    # ── photo: s3_key ────────────────────────────────────────────────────────
    op.add_column(
        'photo',
        sa.Column('s3_key', sa.String(), nullable=True)
    )
    # Backfill: extract S3 key from the stored full URL.
    # URL format: https://<bucket>.s3.<region>.amazonaws.com/<key>
    op.execute("""
        UPDATE photo
        SET s3_key = split_part(media_url, '.amazonaws.com/', 2)
        WHERE media_url LIKE '%.amazonaws.com/%'
    """)
    op.create_unique_constraint('uq_photo_s3_key', 'photo', ['s3_key'])

    # ── photo: vote_count ────────────────────────────────────────────────────
    op.add_column(
        'photo',
        sa.Column('vote_count', sa.Integer(), nullable=False, server_default='0')
    )
    # Backfill from vote table
    op.execute("""
        UPDATE photo
        SET vote_count = (
            SELECT COUNT(*) FROM vote WHERE vote.photo_id = photo.id
        )
    """)

    # ── post: total_votes ────────────────────────────────────────────────────
    op.add_column(
        'post',
        sa.Column('total_votes', sa.Integer(), nullable=False, server_default='0')
    )
    # Backfill from vote table
    op.execute("""
        UPDATE post
        SET total_votes = (
            SELECT COUNT(*) FROM vote WHERE vote.post_id = post.id
        )
    """)

    # ── vote: voted_at (new explicit column, mirrors created_at) ─────────────
    # The Vote model now uses voted_at as the primary timestamp column.
    # We add it and populate it from created_at so history is preserved.
    op.add_column(
        'vote',
        sa.Column('voted_at', sa.DateTime(), nullable=True)
    )
    op.execute("UPDATE vote SET voted_at = created_at WHERE voted_at IS NULL")
    # Make it NOT NULL now that every row has a value
    op.alter_column('vote', 'voted_at', nullable=False)


def downgrade() -> None:
    op.drop_column('vote', 'voted_at')
    op.drop_column('post', 'total_votes')
    op.drop_constraint('uq_photo_s3_key', 'photo', type_='unique')
    op.drop_column('photo', 'vote_count')
    op.drop_column('photo', 's3_key')
    op.drop_column('fb_user', 'last_seen_at')
