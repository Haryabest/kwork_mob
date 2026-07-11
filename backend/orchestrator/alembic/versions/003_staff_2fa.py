"""staff totp fields

Revision ID: 003_staff_2fa
Revises: 002_web
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003_staff_2fa"
down_revision: Union[str, None] = "002_web"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("totp_secret", sa.String(length=64), nullable=True))
    op.add_column(
        "users",
        sa.Column("totp_enabled", sa.Boolean(), server_default="false", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("users", "totp_enabled")
    op.drop_column("users", "totp_secret")
