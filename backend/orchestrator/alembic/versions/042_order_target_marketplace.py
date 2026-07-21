"""target_marketplace on orders §6.6.3"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "042_order_target_marketplace"
down_revision = "041_autoscaling_auto_launch"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column("target_marketplace", sa.String(length=20), nullable=False, server_default="ozon"),
    )


def downgrade() -> None:
    op.drop_column("orders", "target_marketplace")
