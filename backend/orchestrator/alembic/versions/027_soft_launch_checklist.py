"""soft_launch_checklist singleton (§ soft launch panel).

Revision ID: 027_soft_launch_checklist
Revises: 026_alert_thresholds_api_daily
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "027_soft_launch_checklist"
down_revision: Union[str, None] = "026_alert_thresholds_api_daily"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "soft_launch_checklist",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "checks",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("updated_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.execute(
        "INSERT INTO soft_launch_checklist (id, checks) VALUES (1, '{}'::jsonb) "
        "ON CONFLICT DO NOTHING"
    )


def downgrade() -> None:
    op.drop_table("soft_launch_checklist")
