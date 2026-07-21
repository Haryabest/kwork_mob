"""users marketing profile fields §2.6"""

from alembic import op
import sqlalchemy as sa

revision = "039_user_marketing"
down_revision = "038_user_locale"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("gender", sa.String(length=20), nullable=True))
    op.add_column("users", sa.Column("region", sa.String(length=128), nullable=True))
    op.add_column("users", sa.Column("card_bank_issuer", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "card_bank_issuer")
    op.drop_column("users", "region")
    op.drop_column("users", "gender")
