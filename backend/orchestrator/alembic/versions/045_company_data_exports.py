"""company_data_exports §9.5.2"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "045_company_data_exports"
down_revision = "044_user_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "company_data_exports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("requested_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column("notify_email", sa.String(length=255), nullable=True),
        sa.Column("storage_bucket", sa.String(length=128), nullable=True),
        sa.Column("storage_key", sa.String(length=512), nullable=True),
        sa.Column("download_url", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("zip_bytes", sa.Integer(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_company_data_exports_company_id", "company_data_exports", ["company_id"])
    op.create_index("ix_company_data_exports_status", "company_data_exports", ["status"])


def downgrade() -> None:
    op.drop_index("ix_company_data_exports_status", table_name="company_data_exports")
    op.drop_index("ix_company_data_exports_company_id", table_name="company_data_exports")
    op.drop_table("company_data_exports")
