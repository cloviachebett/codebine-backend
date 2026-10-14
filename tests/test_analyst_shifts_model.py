import uuid
from datetime import timedelta

import pytest

from models._types import utcnow
from models.analyst_shifts_model import AnalystShift
import tests.factories as factories


def test_shift_starts_open_with_check_in_time(session):
    analyst = factories.make_user()
    shift = AnalystShift(analyst=analyst)
    session.add(shift)
    session.flush()

    assert shift.checked_out_at is None
    assert shift.checked_in_at is not None


def test_check_out_closes_the_shift(session):
    analyst = factories.make_user()
    shift = AnalystShift(
        analyst=analyst,
        checked_in_at=utcnow() - timedelta(minutes=5),
        checked_out_at=utcnow(),
    )
    session.add(shift)
    session.flush()

    assert shift.checked_out_at is not None


def test_analyst_must_exist(session):
    shift = AnalystShift(analyst_id=uuid.uuid4(), checked_in_at=utcnow())
    session.add(shift)
    with pytest.raises(Exception, match=r"FOREIGN KEY|foreign key"):
        session.flush()


def test_check_out_before_check_in_is_rejected(session):
    analyst = factories.make_user()
    shift = AnalystShift(
        analyst=analyst,
        checked_in_at=utcnow(),
        checked_out_at=utcnow() - timedelta(minutes=5),
    )
    session.add(shift)
    with pytest.raises(Exception, match=r"ck_shift_checkout_after_checkin"):
        session.flush()


def test_user_lists_their_shifts(session):
    analyst = factories.make_user()
    session.add_all([AnalystShift(analyst=analyst), AnalystShift(analyst=analyst)])
    session.flush()
    session.refresh(analyst)

    assert len(analyst.shifts) == 2


def test_deleting_the_analyst_deletes_their_shifts(session):
    analyst = factories.make_user()
    shift = AnalystShift(analyst=analyst)
    session.add(shift)
    session.flush()

    session.delete(analyst)
    session.flush()

    assert session.query(AnalystShift).count() == 0
