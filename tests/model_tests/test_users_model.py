from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, StatementError

from models._enums import AccountStatus, UserRole
from models.incident_reports import IncidentReport
from models.system_audit_logs import SystemAuditLog
from models.users import User


def test_new_user_defaults_to_active_analyst(db_session, make_user, assert_recent_utc):
    user = make_user()
    db_session.add(user)
    db_session.flush()

    assert user.role is UserRole.ANALYST
    assert user.account_status is AccountStatus.ACTIVE
    assert user.last_login_at is None
    assert user.phone is None
    assert user.mfa_enrolled is False
    assert user.failed_login_attempts == 0
    assert user.locked_until is None
    assert_recent_utc(user.created_at)


def test_admin_requires_mfa_and_lockout_state(make_user):
    admin = make_user(role=UserRole.ADMIN)
    analyst = make_user(role=UserRole.ANALYST)

    admin.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)
    assert admin.requires_mfa is True
    assert admin.is_locked is True
    assert analyst.requires_mfa is False


def test_email_must_be_unique(db_session, make_user):
    db_session.add(make_user(email="ana@example.com"))
    db_session.flush()
    db_session.add(make_user(email="ana@example.com"))
    with pytest.raises(IntegrityError):
        db_session.flush()


@pytest.mark.parametrize("column", ["full_name", "email", "password_hash"])
def test_required_columns_reject_null(db_session, column, make_user):
    db_session.add(make_user(**{column: None}))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_password_hash_is_stored_verbatim(db_session, make_user):
    hashed = "$argon2id$v=19$m=65536,t=3,p=4$c29tZXNhbHQ$aGFzaA"
    user = make_user(password_hash=hashed)
    db_session.add(user)
    db_session.commit()
    db_session.expire_all()

    assert db_session.get(User, user.user_id).password_hash == hashed


@pytest.mark.parametrize("role", list(UserRole))
def test_every_role_can_be_stored(db_session, role, make_user):
    user = make_user(role=role)
    db_session.add(user)
    db_session.commit()
    db_session.expire_all()
    assert db_session.get(User, user.user_id).role is role


def test_unknown_role_is_rejected(db_session, make_user):
    db_session.add(make_user(role="SUPERUSER"))
    with pytest.raises(StatementError):
        db_session.flush()


def test_last_login_can_be_recorded(db_session, make_user):
    user = make_user()
    db_session.add(user)
    db_session.commit()

    login_time = datetime(2026, 10, 13, 18, 30, tzinfo=timezone.utc)
    user.last_login_at = login_time
    db_session.commit()
    db_session.expire_all()

    stored = db_session.get(User, user.user_id).last_login_at

    assert stored.replace(tzinfo=None) == login_time.replace(tzinfo=None)


def test_account_can_be_suspended_and_reactivated(db_session, make_user):
    user = make_user()
    db_session.add(user)
    db_session.commit()

    user.account_status = AccountStatus.SUSPENDED
    db_session.commit()
    db_session.expire_all()
    assert db_session.get(User, user.user_id).account_status is AccountStatus.SUSPENDED

    user.account_status = AccountStatus.ACTIVE
    db_session.commit()
    db_session.expire_all()
    assert db_session.get(User, user.user_id).account_status is AccountStatus.ACTIVE


def test_user_exposes_their_reports_reviews_and_audit_logs(
    db_session,
    make_user,
    make_sector,
    make_inference,
    make_incident,
    make_review,
    make_audit_log,
):
    user = make_user()
    sector = make_sector()
    inference = make_inference(sector)
    report = make_incident(sector, reported_by_user=user)
    review = make_review(user, inference=inference)
    log = make_audit_log(user=user)
    db_session.add_all([user, report, review, log])
    db_session.flush()

    assert user.incident_reports == [report]
    assert user.risk_reviews == [review]
    assert user.audit_logs == [log]


def test_deleting_a_user_keeps_their_audit_logs_and_reports(
    db_session, make_user, make_sector, make_incident, make_audit_log
):
    user = make_user()
    sector = make_sector()
    db_session.add_all(
        [
            user,
            make_incident(sector, reported_by_user=user),
            make_audit_log(user=user),
        ]
    )
    db_session.commit()

    db_session.delete(user)
    db_session.commit()

    log = db_session.scalars(select(SystemAuditLog)).one()
    report = db_session.scalars(select(IncidentReport)).one()
    assert log.user_id is None
    assert report.reported_by is None


def test_a_user_who_made_review_decisions_cannot_be_deleted(
    db_session, make_user, make_inference, make_sector, make_review
):
    user = make_user()
    inference = make_inference(make_sector())
    db_session.add_all([user, make_review(user, inference=inference)])
    db_session.commit()

    db_session.delete(user)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
    assert db_session.query(User).count() == 1
