import logging
from time import perf_counter
from typing import Annotated

from pydantic import BaseModel, Field
from cachetools.func import ttl_cache
from fastapi.exceptions import HTTPException
from fastapi import Path, Query
from fastapi.routing import APIRouter
from requests import Response
from enum import Enum

from src.backend.riotapi.client.httpx_riotclient import get_riotclient
from src.backend.riotapi.routes._region import REGION_ANNOTATED_PATTERN, GetRiotClientByUserRegionToContinent, \
    QueryToRiotAPI
from src.utils.static import MINUTE


# ==================================================================================================
class LolChallengesV1_Endpoints:
    ChallengeConfigInfo: str = '/lol/challenges/v1/challenges/config'
    ChallengeConfigInfoByChallengeId: str = '/lol/challenges/v1/challenges/{challengeId}/config'
    PercentileLevel: str = '/lol/challenges/v1/challenges/percentiles'
    PercentileLevelByChallengeId: str = '/lol/challenges/v1/challenges/{challengeId}/percentiles'


class State(str, Enum):
    DISABLED: str = Field("DISABLED", description="Not visible and not calculated")
    HIDDEN: str = Field("HIDDEN", description="Not visible but calculated")
    ENABLED: str = Field("ENABLED", description="Visible and calculated")
    ARCHIVED: str = Field("ARCHIVED", description="Visible but not calculated")


class Tracking(str, Enum):
    LIFETIME: str = Field("LIFETIME", description="Stats are incremented without reset")
    SEASON: str = Field("SEASON", description="Stats are accumulated by season and reset at the beginning of new season")


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


# ==================================================================================================
router = APIRouter()


# ==================================================================================================
# Challenge Config
@ttl_cache(maxsize=1, ttl=30*MINUTE, timer=perf_counter, typed=True)
@router.get("/challenge/config", response_model=list[ChallengeConfigInfoDto])
async def ListChallengeConfigInfoDto(
        region: Annotated[str, Query(pattern=REGION_ANNOTATED_PATTERN)]
    ) -> list[ChallengeConfigInfoDto]:
    f"""
    {LolChallengesV1_Endpoints.ChallengeConfigInfo}
    List of all basic challenge configuration information (includes all translations for names and descriptions)

    Arguments:
    ---------

    - query::region (str)
        The region to query against as.

    """
    client = GetRiotClientByUserRegionToContinent(region, src_route=str(__name__), router=router,
                                                  bypass_region_route=True)
    endpoint: str = LolChallengesV1_Endpoints.ChallengeConfigInfo
    return await QueryToRiotAPI(client, endpoint)


@ttl_cache(maxsize=64, ttl=30*MINUTE, timer=perf_counter, typed=True)
@router.get("/challenge/config/{challengeId}", response_model=ChallengeConfigInfoDto)
async def GetChallengeConfigInfoDto(
        challengeId: str,
        region: Annotated[str, Query(pattern=REGION_ANNOTATED_PATTERN)]
    ) -> ChallengeConfigInfoDto:
    f"""
    {LolChallengesV1_Endpoints.ChallengeConfigInfoByChallengeId}
    Get of basic challenge configuration information (includes all translations for names and descriptions) 
    based on the challenge id.

    Arguments:
    ---------
    
    - path::challengeId (str)
        The id of the challenge to query against as.
    
    - query::region (str)
        The region to query against as.

    """
    client = GetRiotClientByUserRegionToContinent(region, src_route=str(__name__), router=router,
                                                  bypass_region_route=True)
    endpoint: str = LolChallengesV1_Endpoints.ChallengeConfigInfoByChallengeId.format(challengeId=challengeId)
    return await QueryToRiotAPI(client, endpoint)


@ttl_cache(maxsize=1, ttl=30*MINUTE, timer=perf_counter, typed=True)
@router.get("/challenge/percentiles", response_model=dict[int, dict[str, float]])
async def ListPercentileLevel(
        region: Annotated[str, Path(pattern=REGION_ANNOTATED_PATTERN)]
    ) -> dict[int, dict[str, float]]:
    f"""
    {LolChallengesV1_Endpoints.ChallengeConfigInfo}
    List of all basic level to percentile of players who have achieved it 
    - keys: ChallengeId -> Season -> Level -> percentile of players who achieved it

    Arguments:
    ---------

    - path::region (str)
        The region to query against as.

    """
    client = GetRiotClientByUserRegionToContinent(region, src_route=str(__name__), router=router,
                                                  bypass_region_route=True)
    endpoint: str = LolChallengesV1_Endpoints.PercentileLevel
    return await QueryToRiotAPI(client, endpoint)


@ttl_cache(maxsize=64, ttl=30*MINUTE, timer=perf_counter, typed=True)
@router.get("/challenge/percentiles/{challengeId}", response_model=dict[str, float])
async def GetPercentileLevelByChallengeId(
        challengeId: str,
        region: Annotated[str, Path(pattern=REGION_ANNOTATED_PATTERN)]
    ) -> dict[str, float]:
    f"""
    {LolChallengesV1_Endpoints.PercentileLevelByChallengeId}
    Get of basic level to percentile of players who have achieved it based on the challenge id.

    Arguments:
    ---------
    
    - path::challengeId (str)
        The id of the challenge to query against as.
    
    - path::region (str)
        The region to query against as.

    """
    client = GetRiotClientByUserRegionToContinent(region, src_route=str(__name__), router=router,
                                                  bypass_region_route=True)
    endpoint: str = LolChallengesV1_Endpoints.PercentileLevelByChallengeId.format(challengeId=challengeId)
    return await QueryToRiotAPI(client, endpoint)
