"""cloud_publication_ha

Revision ID: 012_cloud_pub
Revises: 011_b2b_ha
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "012_cloud_pub"
down_revision: Union[str, None] = "011_b2b_ha"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cloud_instances",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider", sa.String(30), nullable=False),
        sa.Column("instance_id", sa.String(128), nullable=False),
        sa.Column("worker_id", sa.String(64), nullable=False),
        sa.Column("gpu", sa.String(64), nullable=False),
        sa.Column("status", sa.String(30), server_default="starting"),
        sa.Column("image", sa.Text(), nullable=True),
        sa.Column("public_ip", sa.String(64), nullable=True),
        sa.Column("tailscale_ip", sa.String(64), nullable=True),
        sa.Column("rub_per_hour", sa.Integer(), server_default="0"),
        sa.Column("meta", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stopped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_cloud_instances_instance_id", "cloud_instances", ["instance_id"])
    op.create_index("ix_cloud_instances_worker_id", "cloud_instances", ["worker_id"])

    op.create_table(
        "cloud_operations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider", sa.String(30), nullable=False),
        sa.Column("instance_id", sa.String(128), nullable=True),
        sa.Column("action", sa.String(30), nullable=False),
        sa.Column("ok", sa.Boolean(), server_default="true"),
        sa.Column("details", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_table(
        "cloud_costs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider", sa.String(30), nullable=False),
        sa.Column("instance_id", sa.String(128), nullable=True),
        sa.Column("worker_id", sa.String(64), nullable=True),
        sa.Column("gpu", sa.String(64), nullable=True),
        sa.Column("hours", sa.Float(), server_default="0"),
        sa.Column("amount_rub", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_table(
        "autoscaling_rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("queue_threshold", sa.Integer(), server_default="20"),
        sa.Column("launch_count", sa.Integer(), server_default="1"),
        sa.Column("provider", sa.String(30), server_default="intelion"),
        sa.Column("gpu", sa.String(64), server_default="rtx4090"),
        sa.Column("image", sa.Text(), nullable=True),
        sa.Column("idle_timeout_min", sa.Integer(), server_default="30"),
        sa.Column("max_cloud_workers", sa.Integer(), server_default="5"),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_table(
        "model_publication_links",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("model_uuid", sa.String(36), nullable=False),
        sa.Column("marketplace", sa.String(20), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("last_check_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("check_attempts", sa.Integer(), server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_model_publication_links_model_uuid", "model_publication_links", ["model_uuid"])
    op.create_table(
        "publication_bonuses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=True),
        sa.Column("model_uuid", sa.String(36), nullable=False),
        sa.Column("bonus_type", sa.String(30), nullable=False),
        sa.Column("bonus_value", sa.Integer(), server_default="0"),
        sa.Column("promocode_id", sa.Integer(), nullable=True),
        sa.Column("awarded_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_table(
        "model_share_links",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("short_hash", sa.String(16), nullable=False),
        sa.Column("model_uuid", sa.String(36), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_model_share_links_short_hash", "model_share_links", ["short_hash"], unique=True)
    op.create_table(
        "publication_bonus_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("bonus_type", sa.String(30), server_default="discount_percent"),
        sa.Column("bonus_value", sa.Integer(), server_default="10"),
        sa.Column("promocode_ttl_days", sa.Integer(), server_default="30"),
        sa.Column("max_uses", sa.Integer(), server_default="1"),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
    )
    op.execute(
        "INSERT INTO publication_bonus_settings (id, bonus_type, bonus_value) VALUES (1, 'discount_percent', 10) "
        "ON CONFLICT DO NOTHING"
    )


def downgrade() -> None:
    for t in (
        "publication_bonus_settings",
        "model_share_links",
        "publication_bonuses",
        "model_publication_links",
        "autoscaling_rules",
        "cloud_costs",
        "cloud_operations",
        "cloud_instances",
    ):
        op.drop_table(t)
