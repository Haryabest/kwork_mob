"""service_log_events — PG fallback для /admin/logs (§11.5).

Revision ID: 017_service_logs
Revises: 016_b2b_ops
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "017_service_logs"
down_revision: Union[str, None] = "016_b2b_ops"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "service_log_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("level", sa.String(16), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("worker_id", sa.String(64), nullable=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=True),
        sa.Column("task_id", sa.String(64), nullable=True),
        sa.Column("details", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_service_log_events_source", "service_log_events", ["source"])
    op.create_index("ix_service_log_events_level", "service_log_events", ["level"])
    op.create_index("ix_service_log_events_worker_id", "service_log_events", ["worker_id"])
    op.create_index("ix_service_log_events_task_id", "service_log_events", ["task_id"])
    op.create_index("ix_service_log_events_created_at", "service_log_events", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_service_log_events_created_at", table_name="service_log_events")
    op.drop_index("ix_service_log_events_task_id", table_name="service_log_events")
    op.drop_index("ix_service_log_events_worker_id", table_name="service_log_events")
    op.drop_index("ix_service_log_events_level", table_name="service_log_events")
    op.drop_index("ix_service_log_events_source", table_name="service_log_events")
    op.drop_table("service_log_events")
