import uuid
from datetime import timedelta

import pytest

from models._types import utcnow
from models.analyst_shifts import AnalystShift


def test_shift_starts_open_with_check_in_time(db_session, make_user):
    analyst = make_user()
    shift = AnalystShift(analyst=analyst)
    db_session.add(shift)
    db_session.flush()

    assert shift.checked_out_at is None
    assert shift.checked_in_at is not None


def test_check_out_closes_the_shift(db_session, make_user):
    analyst = make_user()
    shift = AnalystShift(
        analyst=analyst,
        checked_in_at=utcnow() - timedelta(minutes=5),
        checked_out_at=utcnow(),
    )
    db_session.add(shift)
    db_session.flush()

    assert shift.checked_out_at is not None


def test_analyst_must_exist(db_session):
    shift = AnalystShift(analyst_id=uuid.uuid4(), checked_in_at=utcnow())
    db_session.add(shift)
    with pytest.raises(Exception, match=r"FOREIGN KEY|foreign key"):
        db_session.flush()


def test_check_out_before_check_in_is_rejected(db_session, make_user):
    analyst = make_user()
    shift = AnalystShift(
        analyst=analyst,
        checked_in_at=utcnow(),
        checked_out_at=utcnow() - timedelta(minutes=5),
    )
    db_session.add(shift)
    with pytest.raises(Exception, match=r"ck_shift_checkout_after_checkin"):
        db_session.flush()


def test_user_lists_their_shifts(db_session, make_user):
    analyst = make_user()
    db_session.add_all([AnalystShift(analyst=analyst), AnalystShift(analyst=analyst)])
    db_session.flush()
    db_session.refresh(analyst)

    assert len(analyst.shifts) == 2


def test_deleting_the_analyst_deletes_their_shifts(db_session, make_user):
    analyst = make_user()
    shift = AnalystShift(analyst=analyst)
    db_session.add(shift)
    db_session.flush()

    db_session.delete(analyst)
    db_session.flush()

    assert db_session.query(AnalystShift).count() == 0
