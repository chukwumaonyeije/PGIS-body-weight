"""add progression_states table

Revision ID: b8557f351d8c
Revises: f72237134bfe
Create Date: 2026-06-09 14:18:40.476294

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b8557f351d8c'
down_revision: Union[str, Sequence[str], None] = 'f72237134bfe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "progression_states",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("pattern", sa.String(length=32), nullable=False),
        sa.Column("current_level", sa.Integer(), nullable=False),
        sa.Column("last_changed", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "pattern", name="uq_progression_user_pattern"),
    )


def downgrade() -> None:
    op.drop_table("progression_states")
