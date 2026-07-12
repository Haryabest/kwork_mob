"""escalations_age_gate

Revision ID: 008_escalations_age
Revises: 007_company_invites
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "008_escalations_age"
down_revision: Union[str, None] = "007_company_invites"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("date_of_birth", sa.Date(), nullable=True))
    op.add_column("users", sa.Column("age_verified_at", sa.DateTime(timezone=True), nullable=True))

    op.add_column(
        "task_queue",
        sa.Column("escalation_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "task_queue",
        sa.Column("processing_started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("task_queue", sa.Column("worker_id", sa.String(length=64), nullable=True))
    op.add_column(
        "task_queue",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("task_queue", "updated_at")
    op.drop_column("task_queue", "worker_id")
    op.drop_column("task_queue", "processing_started_at")
    op.drop_column("task_queue", "escalation_count")
    op.drop_column("users", "age_verified_at")
    op.drop_column("users", "date_of_birth")
