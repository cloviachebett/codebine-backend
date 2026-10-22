from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "28c1a862905f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sectors",
        sa.Column("sector_id", sa.Uuid(), nullable=False),
        sa.Column("province_name", sa.String(length=50), nullable=False),
        sa.Column("district_name", sa.String(length=100), nullable=False),
        sa.Column("sector_name", sa.String(length=50), nullable=False),
        sa.Column("boundary_ref", sa.Text(), nullable=True),
        sa.Column("mean_slope_deg", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column(
            "geology_class",
            sa.Enum(
                *["GRANITE", "QUARTZITE", "SCHIST", "PEGMATITE", "ALLUVIUM"],
                name="geology_class_enum",
            ),
            nullable=True,
        ),
        sa.Column("soil_features", sa.JSON(), nullable=True),
        sa.Column("land_cover_class", sa.String(length=100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint("sector_id", name="pk_sectors"),
        sa.UniqueConstraint(
            "district_name", "sector_name", name="uq_sectors_district_sector"
        ),
        sa.CheckConstraint("mean_slope_deg >= 0", name="ck_sectors_slope_non_negative"),
    )
    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('95e61059-2599-5d5a-a11b-7eda10654490', 'Western Province', 'Karongi', 'BWISHYURA', 'Built-Up Area', 34.39, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/bwishyura.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('a62ac167-4a61-5a0b-8879-622682503956', 'Western Province', 'Karongi', 'GASHARI', 'Grass/Shrubland', 35.49, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/gashari.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('30351cd0-6353-5ebf-acac-aad64d1c7c39', 'Western Province', 'Karongi', 'GISHYITA', 'Grass/Shrubland', 31.42, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/gishyita.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('f40d02fb-20fb-58d6-9e29-fe3c053c486a', 'Western Province', 'Karongi', 'GITESI', 'Grass/Shrubland', 35.07, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/gitesi.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('902bbe96-3954-57ca-a9ee-8c817b514d05', 'Western Province', 'Karongi', 'MUBUGA', 'Grass/Shrubland', 34.59, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/mubuga.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('1f73e509-19ca-59eb-8b5e-27cb363b0d12', 'Western Province', 'Karongi', 'MURAMBI', 'Built-Up Area', 22.18, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/murambi.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('f1050f9c-d132-5775-afd4-96d467299cbe', 'Western Province', 'Karongi', 'MURUNDI', 'Cropland', 32.12, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/murundi.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('07a34c41-b71e-57b2-97b2-4fdcaf3e61b0', 'Western Province', 'Karongi', 'MUTUNTU', 'Grass/Shrubland', 22.5, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/mutuntu.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('908c4069-349b-5a17-829b-9cb70e293210', 'Western Province', 'Karongi', 'RUBENGERA', 'Built-Up Area', 25.25, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/rubengera.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('18a7ff21-54c7-5589-8ecc-9cf5d9f85d91', 'Western Province', 'Karongi', 'RUGABANO', 'Cropland', 28.86, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/rugabano.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('4947c292-d97b-52bb-ae93-9f95e78675f5', 'Western Province', 'Karongi', 'RUGANDA', 'Grass/Shrubland', 35.53, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/ruganda.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('8a80761b-1020-54ab-8144-79e35e66467a', 'Western Province', 'Karongi', 'RWANKUBA', 'Cropland', 24.0, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/rwankuba.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('d4f84832-576e-57e5-9415-7ebf0f39a8fc', 'Western Province', 'Karongi', 'TWUMBA', 'Grass/Shrubland', 27.56, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/twumba.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('64362e08-188d-5689-9773-cb8c7c2c264c', 'Western Province', 'Rutsiro', 'BONEZA', 'Forest', 35.36, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/boneza.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('6fa19622-4cb4-582c-88f8-6347e7d09f2f', 'Western Province', 'Rutsiro', 'GIHANGO', 'Grass/Shrubland', 28.04, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/gihango.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('5c009762-4d4f-5551-ac8f-30f446d7a8e7', 'Western Province', 'Rutsiro', 'KIGEYO', 'Forest', 33.21, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/kigeyo.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('9069fa2b-81a4-513b-80e3-447f1fc6c0e4', 'Western Province', 'Rutsiro', 'KIVUMU', 'Cropland', 31.63, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/kivumu.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('85e61b59-74a1-5c41-90c4-7352d54a5800', 'Western Province', 'Rutsiro', 'MANIHIRA', 'Cropland', 22.57, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/manihira.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('c513c211-3fc2-55ba-bc89-31c1542ac763', 'Western Province', 'Rutsiro', 'MUKURA', 'Built-Up Area', 26.78, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/mukura.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('dcb3755d-c54a-5a99-8b01-2175486081e8', 'Western Province', 'Rutsiro', 'MURUNDA', 'Cropland', 20.66, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/murunda.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('eb6f1026-137d-5fec-b7b0-a10fb90c74bf', 'Western Province', 'Rutsiro', 'MUSASA', 'Forest', 32.93, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/musasa.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('473da7e7-b345-5393-85c3-814903350c7f', 'Western Province', 'Rutsiro', 'MUSHONYI', 'Forest', 36.75, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/mushonyi.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('057c8823-f345-5e04-a4a0-72210c90a2c2', 'Western Province', 'Rutsiro', 'MUSHUBATI', 'Cropland', 28.79, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/mushubati.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('c23db626-1976-5b52-b977-4661cfb511b2', 'Western Province', 'Rutsiro', 'NYABIRASI', 'Cropland', 30.71, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/nyabirasi.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('4f1f724a-57d2-5e72-b2c5-f1954057ab61', 'Western Province', 'Rutsiro', 'RUHANGO', 'Built-Up Area', 29.77, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/ruhango.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('5ab03526-74a0-5342-81da-05655022dcee', 'Western Province', 'Rutsiro', 'RUSEBEYA', 'Cropland', 19.22, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/rusebeya.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('f76d4844-5a2b-5442-ab01-64a85ed23efc', 'Western Province', 'Rubavu', 'BUGESHI', 'Cropland', 32.8, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/bugeshi.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('88b19320-1a46-5ac0-84f2-dbc13eb45d15', 'Western Province', 'Rubavu', 'BUSASAMANA', 'Built-Up Area', 31.59, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/busasamana.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('93d141f4-de7b-55e4-afb6-c2d00ea6c30e', 'Western Province', 'Rubavu', 'CYANZARWE', 'Cropland', 18.94, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/cyanzarwe.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('ec2e0b3e-ecbc-5e9f-a452-9c1fe39c6c4b', 'Western Province', 'Rubavu', 'GISENYI', 'Built-Up Area', 24.33, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/gisenyi.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('992ec9b8-7336-549b-8cd7-4c7f880258be', 'Western Province', 'Rubavu', 'KANAMA', 'Built-Up Area', 28.33, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/kanama.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('cf2adbac-18d9-5fe9-889e-443e747d9601', 'Western Province', 'Rubavu', 'KANZENZE', 'Built-Up Area', 30.85, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/kanzenze.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('5bdf1ced-16b4-54d8-8d8b-8aab4ea2b07f', 'Western Province', 'Rubavu', 'MUDENDE', 'Cropland', 32.52, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/mudende.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('5a3a4862-6738-5424-9a63-4ee28a44eae0', 'Western Province', 'Rubavu', 'NYAKIRIBA', 'Built-Up Area', 26.88, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/nyakiriba.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('7430df71-cfda-5d64-b53e-216f4169d9b1', 'Western Province', 'Rubavu', 'NYAMYUMBA', 'Built-Up Area', 33.47, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/nyamyumba.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('7ab3565a-bedf-5915-af6d-632065520671', 'Western Province', 'Rubavu', 'NYUNDO', 'Built-Up Area', 22.5, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/nyundo.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('f5b78e35-f2e4-5e13-bfb9-b8cd21117942', 'Western Province', 'Rubavu', 'RUBAVU', 'Built-Up Area', 28.02, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/rubavu.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('1fb2784d-d0e6-5e80-b3c1-f6786d591237', 'Western Province', 'Rubavu', 'RUGERERO', 'Built-Up Area', 28.56, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/rugerero.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('2f3943fb-1b3f-5d6f-b3f5-9a7f48161234', 'Western Province', 'Nyabihu', 'BIGOGWE', 'Built-Up Area', 24.49, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/bigogwe.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('b46e2317-91e1-5fc4-8ef3-cd1e59cf0ca3', 'Western Province', 'Nyabihu', 'JENDA', 'Cropland', 26.21, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/jenda.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('dd36301b-e3f5-5d0a-8f19-db69a7899c34', 'Western Province', 'Nyabihu', 'JOMBA', 'Grass/Shrubland', 34.6, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/jomba.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('70b6f0ba-7cfd-5d0a-accb-f814e41ad159', 'Western Province', 'Nyabihu', 'KABATWA', 'Cropland', 30.16, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/kabatwa.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('3e44dc93-57fc-59e5-a65a-27f20c0a586d', 'Western Province', 'Nyabihu', 'KARAGO', 'Cropland', 19.37, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/karago.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('af4d1bde-34a5-5c82-847e-81b0f427bdbb', 'Western Province', 'Nyabihu', 'KINTOBO', 'Cropland', 30.42, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/kintobo.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('6fea59ee-1d34-5311-b473-7a281e40b868', 'Western Province', 'Nyabihu', 'MUKAMIRA', 'Built-Up Area', 29.12, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/mukamira.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('cbe9b5bd-cb5d-536c-a417-c5b646c8ed7b', 'Western Province', 'Nyabihu', 'MURINGA', 'Cropland', 19.47, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/muringa.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('f7132eec-26cc-5c9a-948d-a740132b9162', 'Western Province', 'Nyabihu', 'RAMBURA', 'Cropland', 32.58, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/rambura.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('3c5b6712-28d2-59b4-91a8-ed4e22c9e863', 'Western Province', 'Nyabihu', 'RUGERA', 'Cropland', 25.25, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/rugera.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('875ad95d-d71e-5019-ae97-42a7246eaf82', 'Western Province', 'Nyabihu', 'RUREMBO', 'Cropland', 35.5, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/rurembo.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('b9c5cb41-3876-527b-9937-9ce463e8b246', 'Western Province', 'Nyabihu', 'SHYIRA', 'Cropland', 24.22, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/shyira.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('ea7ca6d7-51e2-5b64-badd-447c6ad86a13', 'Western Province', 'Ngororero', 'BWIRA', 'Cropland', 23.14, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/bwira.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('d4f4f94b-0ead-5bb3-ab7b-8458b0d7a238', 'Western Province', 'Ngororero', 'GATUMBA', 'Cropland', 33.47, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/gatumba.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('aa8ccacc-a6df-503a-8d7c-5bccb3c68569', 'Western Province', 'Ngororero', 'HINDIRO', 'Cropland', 28.59, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/hindiro.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('f5673dc0-46b7-553a-8921-6a4d13af118b', 'Western Province', 'Ngororero', 'KABAYA', 'Built-Up Area', 25.27, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/kabaya.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('f8d6d845-2c7f-515b-a200-e175ab6b77e0', 'Western Province', 'Ngororero', 'KAGEYO', 'Cropland', 33.23, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/kageyo.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('39e0a235-cbae-59bd-95e5-6163b8c6abb0', 'Western Province', 'Ngororero', 'KAVUMU', 'Cropland', 22.28, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/kavumu.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('74d547fe-3d85-50d6-b3b4-33729a0b3cdf', 'Western Province', 'Ngororero', 'MATYAZO', 'Cropland', 22.41, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/matyazo.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('991b8ef4-96ad-59b3-b6f4-47e5eafcbef5', 'Western Province', 'Ngororero', 'MUHANDA', 'Grass/Shrubland', 31.44, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/muhanda.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('5bbc61ca-cee4-56bd-8907-5c2c0cb42a2c', 'Western Province', 'Ngororero', 'MUHORORO', 'Cropland', 28.39, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/muhororo.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('e42b3995-2050-5d6d-a0eb-93534a81d7bb', 'Western Province', 'Ngororero', 'NDARO', 'Grass/Shrubland', 20.15, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/ndaro.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('6a74a220-a41a-55c4-9c7a-1cbd9b10770e', 'Western Province', 'Ngororero', 'NGORORERO', 'Cropland', 24.89, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/ngororero.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('b9fc5add-4fd8-5407-b57e-27b0c5ef636d', 'Western Province', 'Ngororero', 'NYANGE', 'Built-Up Area', 25.67, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/nyange.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('4d2e197d-d19b-56a8-9e58-914ed46e1a98', 'Western Province', 'Ngororero', 'SOVU', 'Grass/Shrubland', 31.22, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/sovu.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('9cedbcfe-541c-5631-b590-dc71bf66e9ed', 'Western Province', 'Rusizi', 'BUGARAMA', 'Built-Up Area', 29.98, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/bugarama.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('069bb2ce-aac6-5fa9-aeb8-bbc22039a2d1', 'Western Province', 'Rusizi', 'BUTARE', 'Forest', 33.2, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/butare.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('f607ffea-4411-5d00-abac-f3beb37ae185', 'Western Province', 'Rusizi', 'BWEYEYE', 'Built-Up Area', 19.32, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/bweyeye.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('21e5215e-4602-5448-b514-9589d017a556', 'Western Province', 'Rusizi', 'GASHONGA', 'Forest', 24.09, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/gashonga.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('4ff31754-addb-5f6a-b659-a32f8fa14b2e', 'Western Province', 'Rusizi', 'GIHEKE', 'Cropland', 29.7, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/giheke.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('f96b4c65-44a0-555a-a05b-ea1275369f76', 'Western Province', 'Rusizi', 'GIHUNDWE', 'Built-Up Area', 32.21, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/gihundwe.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('d6b9299d-2343-5944-9e2f-501a1b5d47d5', 'Western Province', 'Rusizi', 'GIKUNDAMVURA', 'Forest', 35.96, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/gikundamvura.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('df1faed9-8847-5ac9-83bd-f1e559220353', 'Western Province', 'Rusizi', 'GITAMBI', 'Forest', 34.02, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/gitambi.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('f2de6978-2579-573e-bba8-bca4131a83ea', 'Western Province', 'Rusizi', 'KAMEMBE', 'Built-Up Area', 32.99, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/kamembe.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('45ecfdbb-2901-533c-b1b3-7152b7d53708', 'Western Province', 'Rusizi', 'MUGANZA', 'Built-Up Area', 25.19, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/muganza.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('9ae3a99f-e1ae-5b5f-861a-96730d158747', 'Western Province', 'Rusizi', 'MURURU', 'Built-Up Area', 25.47, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/mururu.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('f067f145-a09e-5a5e-b201-3f1dc3d71c10', 'Western Province', 'Rusizi', 'NKANKA', 'Built-Up Area', 25.67, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/nkanka.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('50dbbc7e-ff07-528f-9445-d4813e2fc260', 'Western Province', 'Rusizi', 'NKOMBO', 'Built-Up Area', 32.07, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/nkombo.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('9f5a567f-c1f8-5a7a-8792-1efc4a93d3e8', 'Western Province', 'Rusizi', 'NKUNGU', 'Forest', 24.11, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/nkungu.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('d9d767b1-3c20-5ecd-b7e9-e7e0becb3592', 'Western Province', 'Rusizi', 'NYAKABUYE', 'Built-Up Area', 35.52, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/nyakabuye.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('1b268424-19df-5692-91be-17daf5d31ec8', 'Western Province', 'Rusizi', 'NYAKARENZO', 'Cropland', 19.6, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/nyakarenzo.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('8e4f60a4-746c-5b96-87ab-f92d1802e9dc', 'Western Province', 'Rusizi', 'NZAHAHA', 'Grass/Shrubland', 21.77, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/nzahaha.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('42095ff8-23bf-5658-96d9-e23aca78b577', 'Western Province', 'Rusizi', 'RWIMBOGO', 'Built-Up Area', 19.58, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/rwimbogo.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('28bb8307-6255-56cb-bf2f-4cfd7257ea8a', 'Western Province', 'Nyamasheke', 'BUSHEKERI', 'Forest', 36.7, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/bushekeri.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('1e0ba69f-403c-50ae-89ad-96101429c044', 'Western Province', 'Nyamasheke', 'BUSHENGE', 'Cropland', 19.85, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/bushenge.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('b1b39043-37d8-5914-8ffc-1fd8a72174c4', 'Western Province', 'Nyamasheke', 'CYATO', 'Forest', 23.83, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/cyato.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('c15196d5-d1af-5a96-b330-c839777ddd48', 'Western Province', 'Nyamasheke', 'GIHOMBO', 'Grass/Shrubland', 26.19, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/gihombo.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('80cf2db1-c6cd-5793-9b92-df19739f7f4b', 'Western Province', 'Nyamasheke', 'KAGANO', 'Built-Up Area', 23.71, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/kagano.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('ee8242c0-16cc-52da-8317-bf4101667ec2', 'Western Province', 'Nyamasheke', 'KANJONGO', 'Built-Up Area', 25.63, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/kanjongo.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('fd3e1532-99db-5ab5-b0ec-0e6e8932bd88', 'Western Province', 'Nyamasheke', 'KARAMBI', 'Forest', 34.71, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/karambi.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('d0b092ab-739f-5261-b13c-d3b5ead9e563', 'Western Province', 'Nyamasheke', 'KARENGERA', 'Forest', 22.54, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/karengera.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('73e0d704-631b-5fb7-8fca-005f1e0c3aeb', 'Western Province', 'Nyamasheke', 'KIRIMBI', 'Grass/Shrubland', 19.32, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/kirimbi.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('5f688226-173a-5c69-a6d3-3705efbd0aaa', 'Western Province', 'Nyamasheke', 'MACUBA', 'Grass/Shrubland', 25.63, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/macuba.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('26ae9a2f-99bc-5617-97ed-ef0c7ffb0573', 'Western Province', 'Nyamasheke', 'MAHEMBE', 'Grass/Shrubland', 21.22, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/mahembe.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('6ec0f7cb-8a2c-533f-82b9-f984e5dac415', 'Western Province', 'Nyamasheke', 'NYABITEKERI', 'Built-Up Area', 31.92, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/nyabitekeri.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('e1193717-7ef8-554e-b051-55dfb662bcb5', 'Western Province', 'Nyamasheke', 'RANGIRO', 'Forest', 26.67, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/rangiro.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('6b180630-f11d-5af0-aab4-127a467b0d4c', 'Western Province', 'Nyamasheke', 'RUHARAMBUGA', 'Forest', 21.58, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/ruharambuga.geojson', NOW()) ON CONFLICT DO NOTHING"
    )

    op.execute(
        "INSERT INTO sectors (sector_id, province_name, district_name, sector_name, land_cover_class, mean_slope_deg, geology_class, soil_features, boundary_ref, created_at) VALUES ('bf61ee0d-9e7d-59c9-a8ff-7f217669d123', 'Western Province', 'Nyamasheke', 'SHANGI', 'Built-Up Area', 22.79, 'SCHIST', '{\"texture\": \"clay loam\", \"depth_cm\": 120}', 'boundaries/shangi.geojson', NOW()) ON CONFLICT DO NOTHING"
    )


def downgrade() -> None:
    op.execute("DELETE FROM sectors")
    op.drop_table("sectors")
