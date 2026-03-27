from __future__ import annotations

from datetime import datetime, timezone


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso_or_none(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()
