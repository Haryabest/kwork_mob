"""autoscaling auto_launch semi-auto §4.7"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "041_autoscaling_auto_launch"
down_revision = "040_refresh_remember_me"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "autoscaling_rules",
        sa.Column("auto_launch", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("autoscaling_rules", "auto_launch")
