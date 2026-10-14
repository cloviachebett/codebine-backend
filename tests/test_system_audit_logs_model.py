import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from models import SystemAuditLog
from tests.factories import make_audit_log, make_user
from tests.helpers import assert_recent_utc


def test_audit_log_persists_and_reloads(session):
    log = make_audit_log(
        action_type="APPROVE_ALERT", entity_type="EMERGENCY_ALERT", entity_id="abc123"
    )
    session.add(log)
    session.commit()
    session.expire_all()

    loaded = session.get(SystemAuditLog, log.log_id)
    assert loaded.action_type == "APPROVE_ALERT"
    assert loaded.entity_type == "EMERGENCY_ALERT"
    assert loaded.entity_id == "abc123"


def test_new_log_gets_a_uuid_and_utc_timestamp(session):
    log = make_audit_log()
    session.add(log)
    session.flush()

    assert isinstance(log.log_id, uuid.UUID)
    assert_recent_utc(log.created_at)


def test_optional_fields_default_to_null(session):
    log = make_audit_log()
    session.add(log)
    session.commit()
    session.expire_all()

    assert log.user_id is None
    assert log.entity_id is None
    assert log.execution_details is None


def test_execution_details_round_trip_as_json(session):
    details = {"ip": "10.0.0.4", "changes": {"status": ["PENDING", "SENT"]}}
    log = make_audit_log(execution_details=details)
    session.add(log)
    session.commit()
    session.expire_all()

    assert log.execution_details == details


def test_log_links_to_the_acting_user_both_ways(session):
    user = make_user()
    log = make_audit_log(user=user)
    session.add(log)
    session.flush()

    assert log.user_id == user.user_id
    assert log.user is user
    assert user.audit_logs == [log]


def test_acting_user_must_exist(session):
    session.add(make_audit_log(user_id=uuid.uuid4()))
    with pytest.raises(IntegrityError):
        session.flush()


@pytest.mark.parametrize("column", ["action_type", "entity_type"])
def test_required_columns_reject_null(session, column):
    session.add(make_audit_log(**{column: None}))
    with pytest.raises(IntegrityError):
        session.flush()
