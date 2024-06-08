from time import perf_counter
from typing import Annotated

from cachetools.func import ttl_cache
from fastapi import Query
from fastapi.routing import APIRouter
from fastapi.responses import Response
from src.backend.riotapi.routes._query import QueryToRiotAPI
from src.static.static import BASE_TTL_ENTRY, BASE_TTL_DURATION, EXTENDED_TTL_DURATION, REGION_ANNOTATED_PATTERN, CREDENTIALS
from src.backend.riotapi.routes._endpoints import LolChallengesV1_Endpoints
from src.backend.riotapi.models.LolChallengesV1 import ChallengeConfigInfoDto, PlayerInfoDto


# ==================================================================================================
router = APIRouter()
SRC_ROUTE: str = str(__name__).split('.')[-1]
_CREDENTIALS = [CREDENTIALS.LOL, CREDENTIALS.FULL]

# ==================================================================================================
# Challenge Config
@ttl_cache(maxsize=1, ttl=EXTENDED_TTL_DURATION, timer=perf_counter, typed=True)
@router.get("/challenge/config", response_model=list[ChallengeConfigInfoDto], tags=[SRC_ROUTE])
async def ListChallengeConfigInfoDto(
        response: Response,
        region: Annotated[str | None, Query(pattern=REGION_ANNOTATED_PATTERN)] = None
) -> list[ChallengeConfigInfoDto]:
    f"""
    {LolChallengesV1_Endpoints.ChallengeConfigInfo}
    List of all basic challenge configuration information (includes all translations for names and descriptions)

    Arguments:
    ---------

    - query::region (str)
        The region to query against as.

    """
    endpoint: str = LolChallengesV1_Endpoints.ChallengeConfigInfo
    return await QueryToRiotAPI(host=region, credentials=_CREDENTIALS, endpoint=endpoint, router=router,
                                method="GET", params=None, headers=None, cookies=None, usr_response=response)


@ttl_cache(maxsize=BASE_TTL_ENTRY, ttl=EXTENDED_TTL_DURATION, timer=perf_counter, typed=True)
@router.get("/challenge/config/{challengeId}", response_model=ChallengeConfigInfoDto, tags=[SRC_ROUTE])
async def GetChallengeConfigInfoDto(
        challengeId: str,
        response: Response,
        region: Annotated[str | None, Query(pattern=REGION_ANNOTATED_PATTERN)] = None,
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
    endpoint: str = LolChallengesV1_Endpoints.ChallengeConfigInfoByChallengeId.format(challengeId=challengeId)
    return await QueryToRiotAPI(host=region, credentials=_CREDENTIALS, endpoint=endpoint, router=router,
                                method="GET", params=None, headers=None, cookies=None, usr_response=response)


@ttl_cache(maxsize=1, ttl=EXTENDED_TTL_DURATION, timer=perf_counter, typed=True)
@router.get("/challenge/percentiles", response_model=dict[int, dict[str, float]], tags=[SRC_ROUTE])
async def ListPercentileLevel(
        response: Response,
        region: Annotated[str | None, Query(pattern=REGION_ANNOTATED_PATTERN)] = None
) -> dict[int, dict[str, float]]:
    f"""
    {LolChallengesV1_Endpoints.ChallengeConfigInfo}
    List of all basic level to percentile of players who have achieved it 
    - keys: ChallengeId -> Season -> Level -> percentile of players who achieved it

    Arguments:
    ---------

    - query::region (str)
        The region to query against as.

    """
    endpoint: str = LolChallengesV1_Endpoints.PercentileLevel
    return await QueryToRiotAPI(host=region, credentials=_CREDENTIALS, endpoint=endpoint, router=router,
                                method="GET", params=None, headers=None, cookies=None, usr_response=response)


@ttl_cache(maxsize=BASE_TTL_ENTRY, ttl=EXTENDED_TTL_DURATION, timer=perf_counter, typed=True)
@router.get("/challenge/percentiles/{challengeId}", response_model=dict[str, float], tags=[SRC_ROUTE])
async def GetPercentileLevelByChallengeId(
        challengeId: str,
        response: Response,
        region: Annotated[str | None, Query(pattern=REGION_ANNOTATED_PATTERN)] = None,
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
    endpoint: str = LolChallengesV1_Endpoints.PercentileLevelByChallengeId.format(challengeId=challengeId)
    return await QueryToRiotAPI(host=region, credentials=_CREDENTIALS, endpoint=endpoint, router=router,
                                method="GET", params=None, headers=None, cookies=None, usr_response=response)


@ttl_cache(maxsize=BASE_TTL_ENTRY, ttl=BASE_TTL_DURATION, timer=perf_counter, typed=True)
@router.get("/player-data/{puuid}", response_model=PlayerInfoDto, tags=[SRC_ROUTE])
async def GetPlayerData(
        puuid: str,
        response: Response,
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
    endpoint: str = LolChallengesV1_Endpoints.PlayerData.format(puuid=puuid)
    return await QueryToRiotAPI(host=region, credentials=_CREDENTIALS, endpoint=endpoint, router=router,
                                method="GET", params=None, headers=None, cookies=None, usr_response=response)
