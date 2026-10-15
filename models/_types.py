import enum
from datetime import datetime, timezone

from sqlalchemy import JSON, Enum
from sqlalchemy.dialects.postgresql import JSONB

JSONVariant = JSONB(none_as_null=True).with_variant(JSON(none_as_null=True), "sqlite")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def enum_column(enum_cls: type[enum.Enum], name: str) -> Enum:
    return Enum(
        enum_cls,
        name=name,
        native_enum=False,
        validate_strings=True,
        create_constraint=True,
    )
