"""UTC timestamp conversion for the existing timezone-naive database columns."""

from datetime import datetime, timezone

from sqlalchemy import DateTime
from sqlalchemy.types import TypeDecorator


class UTCDateTime(TypeDecorator):
    """Store naive UTC; return aware UTC. Legacy naive inputs are treated as UTC."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect):
        if value is None:
            return None
        if value.utcoffset() is not None:
            value = value.astimezone(timezone.utc)
        return value.replace(tzinfo=None)

    def process_result_value(self, value: datetime | None, dialect):
        if value is None:
            return None
        if value.utcoffset() is not None:
            return value.astimezone(timezone.utc)
        return value.replace(tzinfo=timezone.utc)
