"""Helpers de fecha/hora. Se guarda todo en UTC; los "días" de negocio se calculan en settings.timezone."""

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.core.config import get_settings


def local_tz() -> ZoneInfo:
    return ZoneInfo(get_settings().timezone)


def now_utc() -> datetime:
    return datetime.now(UTC)


def now_local() -> datetime:
    return datetime.now(local_tz())


def today_local() -> date:
    return now_local().date()


def as_utc(dt: datetime) -> datetime:
    """SQLite devuelve datetimes naive (guardados en UTC); Postgres los devuelve aware."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def to_local_date(dt: datetime) -> date:
    return as_utc(dt).astimezone(local_tz()).date()


def local_day_start_utc(d: date) -> datetime:
    """Inicio (00:00 local) del día `d`, expresado en UTC."""
    return datetime.combine(d, time.min, tzinfo=local_tz()).astimezone(UTC)


def local_day_bounds_utc(d: date) -> tuple[datetime, datetime]:
    return local_day_start_utc(d), local_day_start_utc(d + timedelta(days=1))
