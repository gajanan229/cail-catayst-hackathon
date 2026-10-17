"""Time helpers: simulated time is a naive datetime treated as UTC and serialized with a trailing Z."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone


def iso_sim(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_sim(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "")).replace(tzinfo=None)


def wall_now() -> str:
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


def hhmm_to_minutes(text: str) -> float:
    parts = [int(p) for p in text.split(":")]
    while len(parts) < 3:
        parts.append(0)
    return parts[0] * 60 + parts[1] + parts[2] / 60


def minutes_of_day(dt: datetime) -> float:
    return dt.hour * 60 + dt.minute + dt.second / 60


def add_s(dt: datetime, seconds: float) -> datetime:
    return dt + timedelta(seconds=seconds)
