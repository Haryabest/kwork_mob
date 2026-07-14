"""Миграция: last_login_at для auto_block_inactive (§2.5.4).

Revision ID: 018_last_login
Revises: 017_service_logs
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "018_last_login"
down_revision: Union[str, None] = "017_service_logs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_users_last_login_at", "users", ["last_login_at"])


def downgrade() -> None:
    op.drop_index("ix_users_last_login_at", table_name="users")
    op.drop_column("users", "last_login_at")
