from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "28c1a862905f"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table("temp_soil_import")
    op.drop_table("stage_lulc")
    op.drop_table("stage_geo")
    op.drop_table("stage_soil_dataset")


def downgrade() -> None:
    op.create_table(
        "stage_soil_dataset",
        sa.Column("sample_id", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column("province", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column("district", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column("sector", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column("longitude", sa.NUMERIC(), autoincrement=False, nullable=True),
        sa.Column("latitude", sa.NUMERIC(), autoincrement=False, nullable=True),
        sa.Column("soil_type", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column("depth", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column("texture", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column("moisture", sa.TEXT(), autoincrement=False, nullable=True),
    )
    op.create_table(
        "stage_geo",
        sa.Column("sector_name", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column("mean_slope", sa.NUMERIC(), autoincrement=False, nullable=True),
        sa.Column("geology_class", sa.TEXT(), autoincrement=False, nullable=True),
    )
    op.create_table(
        "stage_lulc",
        sa.Column("sector_name", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column("land_cover_class", sa.TEXT(), autoincrement=False, nullable=True),
    )
    op.create_table(
        "temp_soil_import",
        sa.Column("province_name", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column("district_name", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column("sector_name", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column("soil_type", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column("depth", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column("texture", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column("moisture", sa.TEXT(), autoincrement=False, nullable=True),
    )
