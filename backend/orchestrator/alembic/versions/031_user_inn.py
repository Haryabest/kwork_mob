"""user.inn для профиля §19.14.1.

Revision ID: 031_user_inn
Revises: 030_model_display_name
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "031_user_inn"
down_revision: Union[str, None] = "030_model_display_name"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("inn", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "inn")
