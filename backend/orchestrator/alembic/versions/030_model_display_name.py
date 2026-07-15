"""model display_name + order model_display_name §19.4.3.

Revision ID: 030_model_display_name
Revises: 029_storage_models_ops
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "030_model_display_name"
down_revision: Union[str, None] = "029_storage_models_ops"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("models", sa.Column("display_name", sa.String(120), nullable=True))
    op.add_column("orders", sa.Column("model_display_name", sa.String(120), nullable=True))


def downgrade() -> None:
    op.drop_column("orders", "model_display_name")
    op.drop_column("models", "display_name")
