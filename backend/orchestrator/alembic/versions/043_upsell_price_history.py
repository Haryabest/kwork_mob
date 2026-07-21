"""upsell_price_history §11.9 / §17.7"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "043_upsell_price_history"
down_revision = "042_order_target_marketplace"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "upsell_price_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("upsell_code", sa.String(length=40), sa.ForeignKey("upsell_prices.code"), nullable=False),
        sa.Column("old_amount", sa.Integer(), nullable=False),
        sa.Column("new_amount", sa.Integer(), nullable=False),
        sa.Column("old_active", sa.Boolean(), nullable=True),
        sa.Column("new_active", sa.Boolean(), nullable=True),
        sa.Column("changed_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_upsell_price_history_code", "upsell_price_history", ["upsell_code"])


def downgrade() -> None:
    op.drop_index("ix_upsell_price_history_code", table_name="upsell_price_history")
    op.drop_table("upsell_price_history")
