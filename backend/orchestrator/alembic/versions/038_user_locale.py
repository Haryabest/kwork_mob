"""users.preferred_locale §16.3"""

from alembic import op
import sqlalchemy as sa

revision = "038_user_locale"
down_revision = "037_user_avatar"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("preferred_locale", sa.String(length=10), nullable=False, server_default="ru"),
    )


def downgrade() -> None:
    op.drop_column("users", "preferred_locale")
