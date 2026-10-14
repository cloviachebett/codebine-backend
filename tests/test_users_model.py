from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, StatementError

from models import IncidentReport, SystemAuditLog, User
from models._enums import AccountStatus, UserRole
from tests.factories import (
    make_audit_log,
    make_incident,
    make_inference,
    make_review,
    make_sector,
    make_user,
)
from tests.helpers import assert_recent_utc, count_rows


def test_new_user_defaults_to_active_analyst(session):
    user = make_user()
    session.add(user)
    session.flush()

    assert user.role is UserRole.ANALYST
    assert user.account_status is AccountStatus.ACTIVE
    assert user.last_login_at is None
    assert user.phone is None
    assert user.mfa_enrolled is False
    assert user.failed_login_attempts == 0
    assert user.locked_until is None
    assert_recent_utc(user.created_at)


def test_admin_requires_mfa_and_lockout_state():
    admin = make_user(role=UserRole.ADMIN)
    analyst = make_user(role=UserRole.ANALYST)

    admin.locked_until = datetime.now(UTC) + timedelta(minutes=15)
    assert admin.requires_mfa is True
    assert admin.is_locked is True
    assert analyst.requires_mfa is False


def test_email_must_be_unique(session):
    session.add(make_user(email="ana@example.com"))
    session.flush()
    session.add(make_user(email="ana@example.com"))
    with pytest.raises(IntegrityError):
        session.flush()


@pytest.mark.parametrize("column", ["full_name", "email", "password_hash"])
def test_required_columns_reject_null(session, column):
    session.add(make_user(**{column: None}))
    with pytest.raises(IntegrityError):
        session.flush()


def test_password_hash_is_stored_verbatim(session):
    hashed = "$argon2id$v=19$m=65536,t=3,p=4$c29tZXNhbHQ$aGFzaA"
    user = make_user(password_hash=hashed)
    session.add(user)
    session.commit()
    session.expire_all()

    assert session.get(User, user.user_id).password_hash == hashed


@pytest.mark.parametrize("role", list(UserRole))
def test_every_role_can_be_stored(session, role):
    user = make_user(role=role)
    session.add(user)
    session.commit()
    session.expire_all()
    assert session.get(User, user.user_id).role is role


def test_unknown_role_is_rejected(session):
    session.add(make_user(role="SUPERUSER"))
    with pytest.raises(StatementError):
        session.flush()


def test_last_login_can_be_recorded(session):
    user = make_user()
    session.add(user)
    session.commit()

    login_time = datetime(2026, 10, 13, 18, 30, tzinfo=UTC)
    user.last_login_at = login_time
    session.commit()
    session.expire_all()

    stored = session.get(User, user.user_id).last_login_at

    assert stored.replace(tzinfo=None) == login_time.replace(tzinfo=None)


def test_account_can_be_suspended_and_reactivated(session):
    user = make_user()
    session.add(user)
    session.commit()

    user.account_status = AccountStatus.SUSPENDED
    session.commit()
    session.expire_all()
    assert session.get(User, user.user_id).account_status is AccountStatus.SUSPENDED

    user.account_status = AccountStatus.ACTIVE
    session.commit()
    session.expire_all()
    assert session.get(User, user.user_id).account_status is AccountStatus.ACTIVE


def test_user_exposes_their_reports_reviews_and_audit_logs(session):
    user = make_user()
    sector = make_sector()
    inference = make_inference(sector)
    report = make_incident(sector, reported_by_user=user)
    review = make_review(user, inference=inference)
    log = make_audit_log(user=user)
    session.add_all([user, report, review, log])
    session.flush()

    assert user.incident_reports == [report]
    assert user.risk_reviews == [review]
    assert user.audit_logs == [log]


def test_deleting_a_user_keeps_their_audit_logs_and_reports(session):
    user = make_user()
    sector = make_sector()
    session.add_all(
        [
            user,
            make_incident(sector, reported_by_user=user),
            make_audit_log(user=user),
        ]
    )
    session.commit()

    session.delete(user)
    session.commit()

    log = session.scalars(select(SystemAuditLog)).one()
    report = session.scalars(select(IncidentReport)).one()
    assert log.user_id is None
    assert report.reported_by is None


def test_a_user_who_made_review_decisions_cannot_be_deleted(session):
    user = make_user()
    inference = make_inference(make_sector())
    session.add_all([user, make_review(user, inference=inference)])
    session.commit()

    session.delete(user)
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()
    assert count_rows(session, User) == 1
