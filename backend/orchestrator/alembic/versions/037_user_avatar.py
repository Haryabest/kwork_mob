"""users.avatar_key §20.8.1"""

from alembic import op
import sqlalchemy as sa

revision = "037_user_avatar"
down_revision = "036_user_oauth_identities"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("avatar_key", sa.String(length=512), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "avatar_key")
