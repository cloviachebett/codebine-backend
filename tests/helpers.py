from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models._types import utcnow


def count_rows(session: Session, model: type) -> int:
    return session.scalar(select(func.count()).select_from(model)) or 0


def assert_recent_utc(value: datetime, seconds: int = 10) -> None:
    assert value.tzinfo is not None
    assert abs(utcnow() - value) < timedelta(seconds=seconds)
