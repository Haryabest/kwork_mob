"""company_webhooks_task_conflicts

Revision ID: 011_b2b_ha
Revises: 010_campaigns_tax_keys
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "011_b2b_ha"
down_revision: Union[str, None] = "010_campaigns_tax_keys"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "company_webhooks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("secret", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("events", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_company_webhooks_company_id", "company_webhooks", ["company_id"])

    op.create_table(
        "company_webhook_deliveries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("webhook_id", sa.Integer(), sa.ForeignKey("company_webhooks.id"), nullable=False),
        sa.Column("event", sa.String(length=50), nullable=False),
        sa.Column("payload", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("ok", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_company_webhook_deliveries_webhook_id",
        "company_webhook_deliveries",
        ["webhook_id"],
    )

    op.create_table(
        "task_conflicts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("task_id", sa.String(length=36), nullable=False),
        sa.Column("worker_id", sa.String(length=64), nullable=True),
        sa.Column("reason", sa.String(length=100), nullable=False),
        sa.Column("details", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_task_conflicts_task_id", "task_conflicts", ["task_id"])


def downgrade() -> None:
    op.drop_index("ix_task_conflicts_task_id", table_name="task_conflicts")
    op.drop_table("task_conflicts")
    op.drop_index("ix_company_webhook_deliveries_webhook_id", table_name="company_webhook_deliveries")
    op.drop_table("company_webhook_deliveries")
    op.drop_index("ix_company_webhooks_company_id", table_name="company_webhooks")
    op.drop_table("company_webhooks")
