from datetime import datetime
from zoneinfo import ZoneInfo
from functools import lru_cache

@lru_cache(maxsize=64, typed=True)
def _load_datetime(year: int, month: int, day: int, hour: int, minute: int, second: int, timezone: str) -> datetime:
    return datetime(year=year, month=month, day=day, hour=hour, minute=minute, second=second, tzinfo=ZoneInfo(timezone))


def check_if_outdated(deadline: dict) -> bool:
    YEAR: int = deadline['YEAR']
    MONTH: int = deadline['MONTH']
    DAY: int = deadline['DAY']
    HOUR: int = deadline['HOUR']
    MINUTE: int = deadline['MINUTE']
    SECOND: int = deadline['SECOND']
    TIMEZONE: int = deadline['TIMEZONE']
    expiry_date = _load_datetime(YEAR, MONTH, DAY, HOUR, MINUTE, SECOND, timezone=TIMEZONE)
    return datetime.now(tz=ZoneInfo('UTC')) > expiry_date