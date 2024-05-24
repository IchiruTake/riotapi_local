"""
This module contains the datetime and TIMEZONE for the project.
For the usage of timezone, we use the zoneinfo and tzdata packages instead of pytz, which is introduced
since Python 3.9. According to the documentation (https://docs.python.org/3/library/zoneinfo.html#module-zoneinfo),
pytz is not recommended for new projects later than Python 3.9 except backward compatibility. By default, zoneinfo uses
the system’s time zone data if available; if no system time zone data is available, the library will fall back to using
the first-party tzdata package available on PyPI.

"""
import logging
from functools import lru_cache
from zoneinfo import ZoneInfo


# ==================================================================================================
__ZONE: str = 'Asia/Saigon'  # 'UTC' or 'Europe/Paris' or 'Asia/Saigon'
__TIMEZONE: ZoneInfo = ZoneInfo(__ZONE)  # ZoneInfo('UTC') or ZoneInfo('Europe/Paris')


@lru_cache(maxsize=16, typed=True)
def SwitchTimezone(zone: str) -> ZoneInfo | None:
    return ZoneInfo(zone)


def SwitchProgramTimezone(zone: str) -> ZoneInfo | None:
    global __ZONE, __TIMEZONE
    try:
        timezone: ZoneInfo = ZoneInfo(zone)
        __ZONE = zone
        __TIMEZONE = timezone
        return __TIMEZONE
    except Exception as e:
        url = 'https://en.wikipedia.org/wiki/List_of_tz_database_time_zones'
        logging.warning(f'Failed to switch the timezone to {zone}, it could be because the tzdata/pytz package is '
                        f'not installed, or mismatched with this {url} (in Linux) or "tzutils.exe /L" in Windows CMD')
        print(e)
    return None


def GetProgramTimezone() -> ZoneInfo:
    return __TIMEZONE


def GetProgramTimezoneName() -> str:
    return __ZONE

