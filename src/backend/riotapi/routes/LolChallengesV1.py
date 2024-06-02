from time import perf_counter
from typing import Annotated

from cachetools.func import ttl_cache
from fastapi import Query
from fastapi.routing import APIRouter
from pydantic import BaseModel, Field
from enum import Enum
from src.backend.riotapi.routes._region import REGION_ANNOTATED_PATTERN, GetRiotClientByUserRegion, \
    QueryToRiotAPI
from src.utils.static import BASE_TTL_ENTRY, BASE_TTL_DURATION, EXTENDED_TTL_DURATION
from src.backend.riotapi.routes._endpoints import LolChallengesV1_Endpoints
from src.backend.riotapi.models.LolChallengesV1 import ChallengeConfigInfoDto, PlayerInfoDto


# ==================================================================================================
router = APIRouter()
SRC_ROUTE: str = str(__name__).split('.')[-1]

# ==================================================================================================
# Challenge Config
@ttl_cache(maxsize=1, ttl=EXTENDED_TTL_DURATION, timer=perf_counter, typed=True)
@router.get("/challenge/config", response_model=list[ChallengeConfigInfoDto], tags=[SRC_ROUTE])
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
    client = GetRiotClientByUserRegion(region, src_route=str(__name__), router=router,
                                       bypass_region_route=True)
    endpoint: str = LolChallengesV1_Endpoints.ChallengeConfigInfo
    return await QueryToRiotAPI(client, endpoint)


@ttl_cache(maxsize=BASE_TTL_ENTRY, ttl=EXTENDED_TTL_DURATION, timer=perf_counter, typed=True)
@router.get("/challenge/config/{challengeId}", response_model=ChallengeConfigInfoDto, tags=[SRC_ROUTE])
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
    client = GetRiotClientByUserRegion(region, src_route=str(__name__), router=router,
                                       bypass_region_route=True)
    endpoint: str = LolChallengesV1_Endpoints.ChallengeConfigInfoByChallengeId.format(challengeId=challengeId)
    return await QueryToRiotAPI(client, endpoint)


@ttl_cache(maxsize=1, ttl=EXTENDED_TTL_DURATION, timer=perf_counter, typed=True)
@router.get("/challenge/percentiles", response_model=dict[int, dict[str, float]], tags=[SRC_ROUTE])
async def ListPercentileLevel(
        region: Annotated[str, Query(pattern=REGION_ANNOTATED_PATTERN)]
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
    client = GetRiotClientByUserRegion(region, src_route=str(__name__), router=router,
                                       bypass_region_route=True)
    endpoint: str = LolChallengesV1_Endpoints.PercentileLevel
    return await QueryToRiotAPI(client, endpoint)


@ttl_cache(maxsize=BASE_TTL_ENTRY, ttl=EXTENDED_TTL_DURATION, timer=perf_counter, typed=True)
@router.get("/challenge/percentiles/{challengeId}", response_model=dict[str, float], tags=[SRC_ROUTE])
async def GetPercentileLevelByChallengeId(
        challengeId: str,
        region: Annotated[str, Query(pattern=REGION_ANNOTATED_PATTERN)]
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
    client = GetRiotClientByUserRegion(region, src_route=str(__name__), router=router,
                                       bypass_region_route=True)
    endpoint: str = LolChallengesV1_Endpoints.PercentileLevelByChallengeId.format(challengeId=challengeId)
    return await QueryToRiotAPI(client, endpoint)


@ttl_cache(maxsize=BASE_TTL_ENTRY, ttl=BASE_TTL_DURATION, timer=perf_counter, typed=True)
@router.get("/player-data/{puuid}", response_model=PlayerInfoDto, tags=[SRC_ROUTE])
async def GetPlayerData(
        puuid: str,
        region: Annotated[str, Query(pattern=REGION_ANNOTATED_PATTERN)]
) -> PlayerInfoDto:
    f"""
    {LolChallengesV1_Endpoints.PlayerData}
    Get player information with list of all progressed challenges

    Arguments:
    ---------

    - path::puuid (str)
        The puuid of the player.
        
    - query::region (str)
        The region to query against as.

    """
    client = GetRiotClientByUserRegion(region, src_route=str(__name__), router=router,
                                       bypass_region_route=True)
    endpoint: str = LolChallengesV1_Endpoints.PlayerData.format(puuid=puuid)
    return await QueryToRiotAPI(client, endpoint)
