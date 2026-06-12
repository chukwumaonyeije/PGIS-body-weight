"""add_auth_fields_to_users

Revision ID: e3c1c64a445a
Revises: 53d30870e36b
Create Date: 2026-06-10 20:48:03.917721

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e3c1c64a445a'
down_revision: Union[str, Sequence[str], None] = '53d30870e36b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("email", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("password_hash", sa.String(length=255), nullable=True))
        batch_op.create_unique_constraint("uq_users_email", ["email"])


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_constraint("uq_users_email", type_="unique")
        batch_op.drop_column("password_hash")
        batch_op.drop_column("email")
