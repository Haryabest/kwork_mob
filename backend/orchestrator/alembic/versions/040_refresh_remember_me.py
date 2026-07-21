"""refresh_tokens.remember_me §2.6"""

from alembic import op
import sqlalchemy as sa

revision = "040_refresh_remember_me"
down_revision = "039_user_marketing"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "refresh_tokens",
        sa.Column("remember_me", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    op.drop_column("refresh_tokens", "remember_me")
