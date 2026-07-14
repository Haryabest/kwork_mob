"""maintenance_checklist singleton §23.7.

Revision ID: 028_maintenance_checklist
Revises: 027_soft_launch_checklist
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "028_maintenance_checklist"
down_revision: Union[str, None] = "027_soft_launch_checklist"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "maintenance_checklist",
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
        "INSERT INTO maintenance_checklist (id, checks) VALUES (1, '{}'::jsonb) "
        "ON CONFLICT DO NOTHING"
    )


def downgrade() -> None:
    op.drop_table("maintenance_checklist")
