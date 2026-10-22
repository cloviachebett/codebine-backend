from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "10b1d2466f66"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "dataset_metadata",
        sa.Column("dataset_id", sa.Uuid(), nullable=False),
        sa.Column("dataset_name", sa.String(length=255), nullable=False),
        sa.Column(
            "factor_type",
            sa.Enum(
                "RAINFALL",
                "TERRAIN",
                "SOIL",
                "GEOLOGY",
                "LAND_COVER",
                "INVENTORY",
                name="dataset_factor_type_enum",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("source_name", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("version", sa.String(length=50), nullable=False),
        sa.Column(
            "processing_status",
            sa.Enum(
                "PENDING",
                "PROCESSING",
                "READY",
                "FAILED",
                name="processing_status_enum",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("last_processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("dataset_id"),
    )
    op.create_index(
        op.f("ix_dataset_metadata_dataset_id"),
        "dataset_metadata",
        ["dataset_id"],
        unique=False,
    )
    op.create_table(
        "model_versions",
        sa.Column("model_version_id", sa.Uuid(), nullable=False),
        sa.Column("model_name", sa.String(length=255), nullable=False),
        sa.Column("version_code", sa.String(length=50), nullable=False),
        sa.Column("model_type", sa.String(length=100), nullable=False),
        sa.Column("model_path", sa.Text(), nullable=False),
        sa.Column(
            "precision",
            postgresql.JSONB(none_as_null=True, astext_type=sa.Text()).with_variant(
                sa.JSON(none_as_null=True), "sqlite"
            ),
            nullable=False,
        ),
        sa.Column(
            "recall",
            postgresql.JSONB(none_as_null=True, astext_type=sa.Text()).with_variant(
                sa.JSON(none_as_null=True), "sqlite"
            ),
            nullable=False,
        ),
        sa.Column(
            "f1_score",
            postgresql.JSONB(none_as_null=True, astext_type=sa.Text()).with_variant(
                sa.JSON(none_as_null=True), "sqlite"
            ),
            nullable=False,
        ),
        sa.Column(
            "model_status",
            sa.Enum(
                "TRAINING",
                "READY",
                "DEPLOYED",
                "ARCHIVED",
                name="model_status_enum",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("model_version_id"),
        sa.UniqueConstraint(
            "model_name", "version_code", name="uq_model_versions_name_version"
        ),
    )
    op.create_index(
        op.f("ix_model_versions_model_version_id"),
        "model_versions",
        ["model_version_id"],
        unique=False,
    )
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
                "GRANITE",
                "QUARTZITE",
                "SCHIST",
                "PEGMATITE",
                "ALLUVIUM",
                name="geology_class_enum",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=True,
        ),
        sa.Column(
            "soil_features",
            postgresql.JSONB(none_as_null=True, astext_type=sa.Text()).with_variant(
                sa.JSON(none_as_null=True), "sqlite"
            ),
            nullable=True,
        ),
        sa.Column("land_cover_class", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("mean_slope_deg >= 0", name="ck_sectors_slope_non_negative"),
        sa.PrimaryKeyConstraint("sector_id"),
        sa.UniqueConstraint(
            "district_name", "sector_name", name="uq_sectors_district_sector"
        ),
    )
    op.create_index(
        op.f("ix_sectors_sector_id"), "sectors", ["sector_id"], unique=False
    )
    op.create_table(
        "users",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column(
            "role",
            sa.Enum(
                "ADMIN",
                "ANALYST",
                name="user_role_enum",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "account_status",
            sa.Enum(
                "ACTIVE",
                "SUSPENDED",
                name="account_status_enum",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("phone", sa.String(length=30), nullable=True),
        sa.Column("mfa_enrolled", sa.Boolean(), nullable=False),
        sa.Column("failed_login_attempts", sa.Integer(), nullable=False),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("user_id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index(op.f("ix_users_user_id"), "users", ["user_id"], unique=False)
    op.create_table(
        "analyst_shifts",
        sa.Column("shift_id", sa.Uuid(), nullable=False),
        sa.Column("analyst_id", sa.Uuid(), nullable=False),
        sa.Column("checked_in_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("checked_out_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_minutes", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.CheckConstraint(
            "checked_out_at IS NULL OR checked_out_at > checked_in_at",
            name="ck_shift_checkout_after_checkin",
        ),
        sa.ForeignKeyConstraint(["analyst_id"], ["users.user_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("shift_id"),
    )
    op.create_index(
        op.f("ix_analyst_shifts_shift_id"), "analyst_shifts", ["shift_id"], unique=False
    )
    op.create_table(
        "incident_reports",
        sa.Column("report_id", sa.Uuid(), nullable=False),
        sa.Column("sector_id", sa.Uuid(), nullable=False),
        sa.Column("reported_by", sa.Uuid(), nullable=True),
        sa.Column("reported_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("event_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("description", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["reported_by"],
            ["users.user_id"],
        ),
        sa.ForeignKeyConstraint(
            ["sector_id"],
            ["sectors.sector_id"],
        ),
        sa.PrimaryKeyConstraint("report_id"),
    )
    op.create_index(
        op.f("ix_incident_reports_report_id"),
        "incident_reports",
        ["report_id"],
        unique=False,
    )
    op.create_table(
        "landslide_inventory",
        sa.Column("landslide_id", sa.Uuid(), nullable=False),
        sa.Column("sector_id", sa.Uuid(), nullable=True),
        sa.Column("event_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("latitude", sa.Numeric(precision=9, scale=6), nullable=False),
        sa.Column("longitude", sa.Numeric(precision=9, scale=6), nullable=False),
        sa.Column(
            "severity",
            sa.Enum(
                "LOW",
                "MEDIUM",
                "HIGH",
                name="landslide_severity_enum",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=True,
        ),
        sa.Column("source_name", sa.String(length=255), nullable=False),
        sa.Column("source_reference", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["sector_id"],
            ["sectors.sector_id"],
        ),
        sa.PrimaryKeyConstraint("landslide_id"),
    )
    op.create_index(
        op.f("ix_landslide_inventory_landslide_id"),
        "landslide_inventory",
        ["landslide_id"],
        unique=False,
    )
    op.create_table(
        "rainfall_matrices",
        sa.Column("rainfall_id", sa.Uuid(), nullable=False),
        sa.Column("sector_id", sa.Uuid(), nullable=False),
        sa.Column("observation_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rain_1day_mm", sa.Numeric(precision=6, scale=2), nullable=False),
        sa.Column("rain_3day_mm", sa.Numeric(precision=6, scale=2), nullable=False),
        sa.Column("rain_7day_mm", sa.Numeric(precision=6, scale=2), nullable=False),
        sa.Column("rain_10day_mm", sa.Numeric(precision=6, scale=2), nullable=False),
        sa.Column("rain_30day_mm", sa.Numeric(precision=6, scale=2), nullable=False),
        sa.Column("dataset_id", sa.Uuid(), nullable=True),
        sa.CheckConstraint(
            "rain_1day_mm >= 0 AND rain_3day_mm >= 0 AND rain_7day_mm >= 0 AND rain_10day_mm >= 0 AND rain_30day_mm >= 0",
            name="ck_rainfall_non_negative",
        ),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["dataset_metadata.dataset_id"],
        ),
        sa.ForeignKeyConstraint(
            ["sector_id"],
            ["sectors.sector_id"],
        ),
        sa.PrimaryKeyConstraint("rainfall_id"),
        sa.UniqueConstraint(
            "sector_id", "observation_time", name="uq_rainfall_sector_time"
        ),
    )
    op.create_index(
        op.f("ix_rainfall_matrices_rainfall_id"),
        "rainfall_matrices",
        ["rainfall_id"],
        unique=False,
    )
    op.create_table(
        "risk_inferences",
        sa.Column("inference_id", sa.Uuid(), nullable=False),
        sa.Column("sector_id", sa.Uuid(), nullable=False),
        sa.Column("model_version_id", sa.Uuid(), nullable=False),
        sa.Column("prediction_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "risk_level",
            sa.Enum(
                "LOW",
                "MODERATE",
                "HIGH",
                "EXTREME",
                name="risk_level_enum",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("risk_score", sa.Numeric(precision=6, scale=5), nullable=False),
        sa.Column("feature_snapshot_id", sa.Uuid(), nullable=True),
        sa.CheckConstraint(
            "risk_score >= 0 AND risk_score <= 1", name="ck_risk_score_range"
        ),
        sa.ForeignKeyConstraint(
            ["model_version_id"],
            ["model_versions.model_version_id"],
        ),
        sa.ForeignKeyConstraint(
            ["sector_id"],
            ["sectors.sector_id"],
        ),
        sa.PrimaryKeyConstraint("inference_id"),
    )
    op.create_index(
        op.f("ix_risk_inferences_feature_snapshot_id"),
        "risk_inferences",
        ["feature_snapshot_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_risk_inferences_inference_id"),
        "risk_inferences",
        ["inference_id"],
        unique=False,
    )
    op.create_table(
        "system_audit_logs",
        sa.Column("log_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("action_type", sa.String(length=100), nullable=False),
        sa.Column("entity_type", sa.String(length=100), nullable=False),
        sa.Column("entity_id", sa.String(length=64), nullable=True),
        sa.Column(
            "execution_details",
            postgresql.JSONB(none_as_null=True, astext_type=sa.Text()).with_variant(
                sa.JSON(none_as_null=True), "sqlite"
            ),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.user_id"],
        ),
        sa.PrimaryKeyConstraint("log_id"),
    )
    op.create_index(
        op.f("ix_system_audit_logs_log_id"),
        "system_audit_logs",
        ["log_id"],
        unique=False,
    )
    op.create_table(
        "emergency_alerts",
        sa.Column("alert_id", sa.Uuid(), nullable=False),
        sa.Column("inference_id", sa.Uuid(), nullable=False),
        sa.Column("sector_id", sa.Uuid(), nullable=False),
        sa.Column("alert_message", sa.Text(), nullable=False),
        sa.Column(
            "severity",
            sa.Enum(
                "LOW",
                "MEDIUM",
                "HIGH",
                "CRITICAL",
                name="alert_severity_enum",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "alert_status",
            sa.Enum(
                "PENDING_REVIEW",
                "APPROVED",
                "REJECTED",
                "DISMISSED",
                name="alert_status_enum",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["inference_id"],
            ["risk_inferences.inference_id"],
        ),
        sa.ForeignKeyConstraint(
            ["sector_id"],
            ["sectors.sector_id"],
        ),
        sa.PrimaryKeyConstraint("alert_id"),
    )
    op.create_index(
        op.f("ix_emergency_alerts_alert_id"),
        "emergency_alerts",
        ["alert_id"],
        unique=False,
    )
    op.create_table(
        "prediction_features",
        sa.Column("feature_snapshot_id", sa.Uuid(), nullable=False),
        sa.Column("inference_id", sa.Uuid(), nullable=False),
        sa.Column(
            "historical_features",
            postgresql.JSONB(none_as_null=True, astext_type=sa.Text()).with_variant(
                sa.JSON(none_as_null=True), "sqlite"
            ),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["inference_id"],
            ["risk_inferences.inference_id"],
        ),
        sa.PrimaryKeyConstraint("feature_snapshot_id"),
        sa.UniqueConstraint("inference_id", name="uq_prediction_features_inference"),
    )
    op.create_index(
        op.f("ix_prediction_features_feature_snapshot_id"),
        "prediction_features",
        ["feature_snapshot_id"],
        unique=False,
    )
    op.create_table(
        "risk_reviews",
        sa.Column("review_id", sa.Uuid(), nullable=False),
        sa.Column("inference_id", sa.Uuid(), nullable=True),
        sa.Column("alert_id", sa.Uuid(), nullable=True),
        sa.Column("reviewed_by", sa.Uuid(), nullable=False),
        sa.Column(
            "decision",
            sa.Enum(
                "APPROVED",
                "REJECTED",
                "DISMISSED",
                name="review_decision_enum",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("comments", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "(inference_id IS NOT NULL AND alert_id IS NULL) OR (inference_id IS NULL AND alert_id IS NOT NULL)",
            name="ck_risk_reviews_single_target",
        ),
        sa.ForeignKeyConstraint(
            ["alert_id"],
            ["emergency_alerts.alert_id"],
        ),
        sa.ForeignKeyConstraint(
            ["inference_id"],
            ["risk_inferences.inference_id"],
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by"],
            ["users.user_id"],
        ),
        sa.PrimaryKeyConstraint("review_id"),
        sa.UniqueConstraint(
            "inference_id", "alert_id", name="uq_risk_reviews_inference_alert"
        ),
    )
    op.create_index(
        op.f("ix_risk_reviews_review_id"), "risk_reviews", ["review_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_risk_reviews_review_id"), table_name="risk_reviews")
    op.drop_table("risk_reviews")
    op.drop_index(
        op.f("ix_prediction_features_feature_snapshot_id"),
        table_name="prediction_features",
    )
    op.drop_table("prediction_features")
    op.drop_index(op.f("ix_emergency_alerts_alert_id"), table_name="emergency_alerts")
    op.drop_table("emergency_alerts")
    op.drop_index(op.f("ix_system_audit_logs_log_id"), table_name="system_audit_logs")
    op.drop_table("system_audit_logs")
    op.drop_index(op.f("ix_risk_inferences_inference_id"), table_name="risk_inferences")
    op.drop_index(
        op.f("ix_risk_inferences_feature_snapshot_id"), table_name="risk_inferences"
    )
    op.drop_table("risk_inferences")
    op.drop_index(
        op.f("ix_rainfall_matrices_rainfall_id"), table_name="rainfall_matrices"
    )
    op.drop_table("rainfall_matrices")
    op.drop_index(
        op.f("ix_landslide_inventory_landslide_id"), table_name="landslide_inventory"
    )
    op.drop_table("landslide_inventory")
    op.drop_index(op.f("ix_incident_reports_report_id"), table_name="incident_reports")
    op.drop_table("incident_reports")
    op.drop_index(op.f("ix_analyst_shifts_shift_id"), table_name="analyst_shifts")
    op.drop_table("analyst_shifts")
    op.drop_index(op.f("ix_users_user_id"), table_name="users")
    op.drop_table("users")
    op.drop_index(op.f("ix_sectors_sector_id"), table_name="sectors")
    op.drop_table("sectors")
    op.drop_index(
        op.f("ix_model_versions_model_version_id"), table_name="model_versions"
    )
    op.drop_table("model_versions")
    op.drop_index(op.f("ix_dataset_metadata_dataset_id"), table_name="dataset_metadata")
    op.drop_table("dataset_metadata")
