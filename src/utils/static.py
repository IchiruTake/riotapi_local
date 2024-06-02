"""
This module contains how we control and manipulate the log format for the project.
This also include a base configuration for the log system, including the default logger and the datetime format.


"""
from cachetools.func import ttl_cache
from enum import StrEnum

# ==================================================================================================
# RegEx Patterns for Logging
YEAR_PATTERN: str = r'%Y'
MONTH_PATTERN: str = r'%m'
DAY_PATTERN: str = r'%d'
HOUR_PATTERN: str = r'%H'
MINUTE_PATTERN: str = r'%M'
SECOND_PATTERN: str = r'%S'
ZONE_PATTERN: str = r'%z'  # Use %Z for timezone name if preferred
ZONENAME_PATTERN: str = r'%Z'  # Use %Z for timezone name if preferred

# Timer part
DATE_PATTERN: str = rf'{YEAR_PATTERN}-{MONTH_PATTERN}-{DAY_PATTERN}'
TIME_PATTERN: str = rf'{HOUR_PATTERN}:{MINUTE_PATTERN}:{SECOND_PATTERN}'
DATETIME_PATTERN_FOR_FILENAME: str = r'%Y-%m-%d_%H-%M-%S'        # r'%Y-%m-%d_%H-%M-%S_%Z'
DATETIME_PATTERN: str = ' '.join([DATE_PATTERN, TIME_PATTERN, ZONE_PATTERN])  # r'%Y-%m-%d %H:%M:%S %z'

# ==================================================================================================
# TIMING
NANOSECOND: float = 1e-9
MICROSECOND: float = 1e-6
MILLISECOND: float = 1e-3
SECOND: int = 1
MINUTE: int = 60 * SECOND
HOUR: int = 60 * MINUTE
DAY: int = 24 * HOUR
WEEK: int = 7 * DAY
MONTH: int = int(30.5 * DAY)
YEAR: int = int(365.25 * DAY)

# ==================================================================================================
# Configurations
REFRESH_RATE_IF_NOT_FOUND: int = 5 * MINUTE     # 5 minutes
MIN_REFRESH_RATE_IF_FOUND: int = 1 * MINUTE    # 1 minutes
RIOTAPI_ENV_CFG_FILE: str = "./conf/riotapi.env.toml"
RIOTAPI_SECRETS_CFG_FILE: str = "./conf/riotapi.secrets.toml"
RIOTAPI_GC_CFG_FILE: str = "./conf/riotapi.gc.toml"
RIOTAPI_LOG_CFG_FILE: str = "./conf/riotapi.log.yaml"

# ==================================================================================================
# Monitoring Interval
SYNC_INTERVAL: int = 90 * SECOND  # 1.5 minutes
INITIAL_SYNC_INTERVAL: int = 15 * SECOND  # Force to have quick data response
INITIAL_SYNC_INTERVAL_DURATION: int = 10 * MINUTE  # 10 minutes

# SQLite Monitoring
SQLITE_DB: str = "riotapi_monitor.db"
SQLITE_PARAMS: dict[str, str] = {
    "timeout": "15",
    "uri": "true",
    "cache": "private",
    "check_same_thread": "true",
}
TRANSACTION_BATCH_SIZE: int = 128
MAX_FAILED_TRANSACTION: int = 3

# ==================================================================================================
ContinentRoute: dict[str, list[str]] = {
    "C1": ["AMERICAS", "EUROPE", "ASIA", "ESPORTS"],
    "C2": ["AMERICAS", "EUROPE", "ASIA", "SEA"]
}
RegionRoute: dict[str, dict[str, str]] = {
    "R1": {"BR1": "AMERICAS", "EUN1": "EUROPE", "EUW1": "EUROPE", "JP1": "ASIA", "KR": "ASIA", "LA1": "AMERICAS",
           "LA2": "AMERICAS", "NA1": "AMERICAS", "OC1": "ASIA", "PH2": "ASIA", "RU": "EUROPE", "SG2": "ASIA",
           "TH2": "ASIA", "TR1": "EUROPE", "TW2": "ASIA", "VN2": "ASIA"},
    "R2": {"BR1": "AMERICAS", "EUN1": "EUROPE", "EUW1": "EUROPE", "JP1": "ASIA", "KR": "ASIA", "LA1": "AMERICAS",
           "LA2": "AMERICAS", "NA1": "AMERICAS", "OC1": "SEA", "PH2": "SEA", "RU": "EUROPE", "SG2": "SEA",
           "TH2": "SEA", "TR1": "EUROPE", "TW2": "SEA", "VN2": "SEA"}
}
_MOUNTLIST: dict[str, str] = {
    "AccountV1": "R1",
    "MatchV5": "R2",
}
for key, value in _MOUNTLIST.items():
    RegionRoute[key] = RegionRoute[value]

class CredentialName(StrEnum):
    FULL: str = "full"
    LOL: str = "lol"
    LOR: str = "lor"
    TFT: str = "tft"
    VAL: str = "val"


# ==================================================================================================
# TTL Cache
BASE_TTL_ENTRY: int = 128
BASE_TTL_MULTIPLIER: int = 16
BASE_TTL_DURATION: int = 5 * MINUTE  # 5 minutes
EXTENDED_TTL_DURATION: int = HOUR # 1 hour
LIFETIME_TTL_DURATION: int = WEEK  # 1 week


@ttl_cache(maxsize=BASE_TTL_ENTRY, ttl=LIFETIME_TTL_DURATION)
def GeneratePattern(source_input: str, account: str, use_values: bool = False) -> str:
    match source_input:
        case "REGION":
            source = RegionRoute[account]
            if use_values:
                return fr'{"|".join(source.values())}'
            return fr'{"|".join(source.keys())}'
        case "CONTINENT":
            return fr'{"|".join(ContinentRoute[account])}'
        case _:
            raise ValueError(f"Invalid source: {source_input}")

REGION_ANNOTATED_PATTERN: str = GeneratePattern("REGION", "R1")
CONTINENT_ANNOTATED_PATTERN: str = GeneratePattern("CONTINENT", "C1")
REGION_TTL_ENTRY: int = BASE_TTL_ENTRY * (REGION_ANNOTATED_PATTERN.count("|") + 1)
CONTINENT_TTL_ENTRY: int = BASE_TTL_ENTRY * (CONTINENT_ANNOTATED_PATTERN.count("|") + 1)

# ==================================================================================================

