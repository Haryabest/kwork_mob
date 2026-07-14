"""models trash/extend + storage node events + disk samples §9.1 / §11.16.

Revision ID: 029_storage_models_ops
Revises: 028_maintenance_checklist
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "029_storage_models_ops"
down_revision: Union[str, None] = "028_maintenance_checklist"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("models", sa.Column("source_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "models",
        sa.Column("source_extend_count", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column("models", sa.Column("trashed_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_models_trashed_at", "models", ["trashed_at"])
    op.create_index("ix_models_source_expires_at", "models", ["source_expires_at"])

    op.create_table(
        "storage_node_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("node_id", sa.String(64), nullable=False),
        sa.Column("node_name", sa.String(128), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_sec", sa.Integer(), nullable=True),
        sa.Column(
            "meta",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.create_index("ix_storage_node_events_node_id", "storage_node_events", ["node_id"])
    op.create_index("ix_storage_node_events_started_at", "storage_node_events", ["started_at"])

    op.create_table(
        "disk_usage_samples",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("used_percent", sa.Float(), nullable=True),
        sa.Column("free_percent", sa.Float(), nullable=True),
        sa.Column("total_bytes", sa.BigInteger(), nullable=True),
        sa.Column(
            "sampled_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_disk_usage_samples_sampled_at", "disk_usage_samples", ["sampled_at"])


def downgrade() -> None:
    op.drop_index("ix_disk_usage_samples_sampled_at", table_name="disk_usage_samples")
    op.drop_table("disk_usage_samples")
    op.drop_index("ix_storage_node_events_started_at", table_name="storage_node_events")
    op.drop_index("ix_storage_node_events_node_id", table_name="storage_node_events")
    op.drop_table("storage_node_events")
    op.drop_index("ix_models_source_expires_at", table_name="models")
    op.drop_index("ix_models_trashed_at", table_name="models")
    op.drop_column("models", "trashed_at")
    op.drop_column("models", "source_extend_count")
    op.drop_column("models", "source_expires_at")
