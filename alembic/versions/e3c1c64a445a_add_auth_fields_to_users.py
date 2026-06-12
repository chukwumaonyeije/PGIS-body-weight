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
    op.add_column('users', sa.Column('email', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('password_hash', sa.String(length=255), nullable=True))
    op.create_unique_constraint('uq_users_email', 'users', ['email'])


def downgrade() -> None:
    op.drop_constraint('uq_users_email', 'users', type_='unique')
    op.drop_column('users', 'password_hash')
    op.drop_column('users', 'email')
