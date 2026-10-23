"""add auth columns to users

Revision ID: 0002_add_auth_columns
Revises: 28c1a862905f
Create Date: 2026-10-23
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002_add_auth_columns"
down_revision: Union[str, Sequence[str], None] = "28c1a862905f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("mfa_secret", sa.String(length=64), nullable=True))
    op.add_column(
        "users",
        sa.Column(
            "is_verified", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )
    op.add_column(
        "users",
        sa.Column("verification_token_hash", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column(
            "verification_token_expires", sa.DateTime(timezone=True), nullable=True
        ),
    )
    op.add_column(
        "users", sa.Column("reset_token_hash", sa.String(length=255), nullable=True)
    )
    op.add_column(
        "users",
        sa.Column("reset_token_expires", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "reset_token_expires")
    op.drop_column("users", "reset_token_hash")
    op.drop_column("users", "verification_token_expires")
    op.drop_column("users", "verification_token_hash")
    op.drop_column("users", "is_verified")
    op.drop_column("users", "mfa_secret")
