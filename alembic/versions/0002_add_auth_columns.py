"""add auth columns to users

Revision ID: 0002_add_auth_columns
Revises: a1b2c3d4e5f6
Create Date: 2026-10-23
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.exc import OperationalError

revision: str = "0002_add_auth_columns"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None

_COLUMNS = [
    ("mfa_secret", sa.Column("mfa_secret", sa.String(length=64), nullable=True)),
    (
        "is_verified",
        sa.Column(
            "is_verified", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    ),
    (
        "verification_token_hash",
        sa.Column("verification_token_hash", sa.String(length=255), nullable=True),
    ),
    (
        "verification_token_expires",
        sa.Column(
            "verification_token_expires", sa.DateTime(timezone=True), nullable=True
        ),
    ),
    (
        "reset_token_hash",
        sa.Column("reset_token_hash", sa.String(length=255), nullable=True),
    ),
    (
        "reset_token_expires",
        sa.Column("reset_token_expires", sa.DateTime(timezone=True), nullable=True),
    ),
]


def upgrade() -> None:
    for name, col in _COLUMNS:
        try:
            op.add_column("users", col)
        except OperationalError:
            pass


def downgrade() -> None:
    for name, _ in _COLUMNS:
        try:
            op.drop_column("users", name)
        except OperationalError:
            pass
