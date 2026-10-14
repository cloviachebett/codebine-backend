import models
from datetime import timezone

import pytest
from sqlalchemy import CheckConstraint, Enum
from sqlalchemy.orm import configure_mappers


from models._types import utcnow
from database import Base

EXPECTED_TABLES = {
    "analyst_shift_table",
    "emergency_alert_table",
    "incident_report_table",
    "landslide_inventory_table",
    "model_version_table",
    "prediction_feature_table",
    "rainfall_matrix_table",
    "risk_inference_table",
    "risk_review_table",
    "sector_table",
    "system_audit_log_table",
    "user_table",
}


def _all_relationships():
    configure_mappers()
    for mapper in Base.registry.mappers:
        yield from mapper.relationships


def test_importing_models_registers_every_table():
    assert set(Base.metadata.tables) == EXPECTED_TABLES


def test_every_model_is_exported_from_the_package():
    mapped = {mapper.class_.__name__ for mapper in Base.registry.mappers}
    assert mapped == set(models.__all__)


def test_all_string_relationships_resolve():
    configure_mappers()


@pytest.mark.parametrize(
    "relationship",
    list(_all_relationships()),
    ids=lambda rel: f"{rel.parent.class_.__name__}.{rel.key}",
)
def test_every_relationship_has_a_matching_other_side(relationship):
    assert relationship.back_populates, "missing back_populates"
    reverse = relationship.mapper.relationships[relationship.back_populates]
    assert reverse.back_populates == relationship.key
    assert reverse.mapper.class_ is relationship.parent.class_


def test_every_enum_column_has_a_database_check_constraint():
    for table in Base.metadata.tables.values():
        check_names = {
            c.name for c in table.constraints if isinstance(c, CheckConstraint)
        }
        for column in table.columns:
            if isinstance(column.type, Enum):
                assert column.type.name in check_names, f"{table.name}.{column.name}"


def test_utcnow_is_timezone_aware_utc():
    assert utcnow().tzinfo == timezone.utc
