from enum import Enum

from pydantic import BaseModel, Field


class State(str, Enum):
    DISABLED: str = Field("DISABLED", description="Not visible and not calculated")
    HIDDEN: str = Field("HIDDEN", description="Not visible but calculated")
    ENABLED: str = Field("ENABLED", description="Visible and calculated")
    ARCHIVED: str = Field("ARCHIVED", description="Visible but not calculated")


class Tracking(str, Enum):
    LIFETIME: str = Field("LIFETIME", description="Stats are incremented without reset")
    SEASON: str = Field("SEASON",
                        description="Stats are accumulated by season and reset at the beginning of new season")


class Level(str, Enum):
    IRON: str = Field("IRON", description="Iron")
    BRONZE: str = Field("BRONZE", description="Bronze")
    SILVER: str = Field("SILVER", description="Silver")
    GOLD: str = Field("GOLD", description="Gold")
    PLATINUM: str = Field("PLATINUM", description="Platinum")
    DIAMOND: str = Field("DIAMOND", description="Diamond")
    MASTER: str = Field("MASTER", description="Master")
    GRANDMASTER: str = Field("GRANDMASTER", description="Grandmaster")
    CHALLENGER: str = Field("CHALLENGER", description="Challenger")


class ChallengeConfigInfoDto(BaseModel):
    id: int
    localizedNames: dict[str, dict[str, str]]
    state: State
    tracking: Tracking
    startTimestamp: int
    endTimestamp: int
    leaderBoard: bool
    thresholds: dict[str, float]


class ChallengePoints(BaseModel):
    level: str
    current: int
    max: int
    percentile: float


class ChallengeInfo(BaseModel):
    challengeId: int
    percentile: float
    level: str
    value: int
    achievedTime: int


class PlayerClientPreferences(BaseModel):
    bannerAccent: str
    title: str
    challengeIds: list[int]
    crestBorder: str
    prestigeCrestBorderLevel: int


class PlayerInfoDto(BaseModel):
    totalPoints: ChallengePoints
    categoryPoints: dict[str, ChallengePoints]
    challenges: list[ChallengeInfo]
    preferences: PlayerClientPreferences

