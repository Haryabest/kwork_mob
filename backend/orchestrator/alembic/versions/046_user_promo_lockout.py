"""User promocode failed attempts and 30-day lockout.

Revision ID: 046_user_promo_lockout
Revises: 045_company_data_exports
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "046_user_promo_lockout"
down_revision: Union[str, None] = "045_company_data_exports"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("promo_failed_attempts", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "users",
        sa.Column("promo_blocked_until", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "promo_blocked_until")
    op.drop_column("users", "promo_failed_attempts")
