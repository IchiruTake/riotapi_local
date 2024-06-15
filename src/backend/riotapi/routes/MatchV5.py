"""
See here for updates:
https://github.com/RiotGames/developer-relations/issues/928

"""

from time import perf_counter
from typing import Annotated

from cachetools.func import ttl_cache
from fastapi import Query
from src.backend.riotapi.inapp import CustomAPIRouter
from fastapi.responses import Response
from httpx import Response as HttpxResponse

from src.backend.riotapi.routes._query import QueryToRiotAPI, PassToStarletteResponse
from src.static.static import BASE_TTL_ENTRY, BASE_TTL_DURATION, CREDENTIALS, MATCH_CONTINENT_ANNOTATED_PATTERN
from src.backend.riotapi.routes._endpoints import MatchV5_Endpoints
from src.backend.riotapi.models.MatchV5 import MatchDto
from src.backend.riotapi.models.MatchV5_Timeline import TimeLineDto


# ==================================================================================================
_CREDENTIALS = [CREDENTIALS.LOL, CREDENTIALS.FULL]
router = CustomAPIRouter()
SRC_ROUTE: str = str(__name__).split('.')[-1]
router.load_profile(name=f"riotapi.routers.{SRC_ROUTE}")


# ==================================================================================================
# Enable Server Caching
MAXSIZE1, TTL1 = router.scale(maxsize=BASE_TTL_ENTRY, ttl=BASE_TTL_DURATION, region_path=False, num_params=1)
MAXSIZE2, TTL2 = router.scale(maxsize=BASE_TTL_ENTRY, ttl=BASE_TTL_DURATION, region_path=False, num_params=2)


@ttl_cache(maxsize=MAXSIZE2, ttl=TTL2, timer=perf_counter, typed=True)
async def _ListMatchesByPuuid(puuid: str, continent: str | None, pattern: str, startTime: int | None = None,
                              endTime: int | None = None, queue: int | None = None, type: str | None = None,
                              start: int = 0, count: int = 20) -> HttpxResponse:
    path_endpoint: str = MatchV5_Endpoints.ListMatchesByPuuid.format(puuid=puuid)
    ops = [('startTime', startTime), ('endTime', endTime), ('queue', queue), ('type', type), ('start', start),
           ('count', count)]
    params = {key: value for key, value in ops if value is not None}
    return await QueryToRiotAPI(host=continent, credentials=_CREDENTIALS, endpoint=path_endpoint, router=router,
                                method="GET", params=params, headers=None, cookies=None, usr_response=None,
                                host_pattern=pattern)

@ttl_cache(maxsize=MAXSIZE1, ttl=TTL1, timer=perf_counter, typed=True)
async def _GetMatch(matchId: str, continent: str | None, pattern: str) -> HttpxResponse:
    path_endpoint: str = MatchV5_Endpoints.GetMatchById.format(matchId=matchId)
    return await QueryToRiotAPI(host=continent, credentials=_CREDENTIALS, endpoint=path_endpoint, router=router,
                                method="GET", params=None, headers=None, cookies=None, usr_response=None,
                                host_pattern=pattern)

@ttl_cache(maxsize=MAXSIZE1, ttl=TTL1, timer=perf_counter, typed=True)
async def _GetMatchTimeline(matchId: str, continent: str | None, pattern: str) -> HttpxResponse:
    path_endpoint: str = MatchV5_Endpoints.GetMatchTimelineById.format(matchId=matchId)
    return await QueryToRiotAPI(host=continent, credentials=_CREDENTIALS, endpoint=path_endpoint, router=router,
                                method="GET", params=None, headers=None, cookies=None, usr_response=None,
                                host_pattern=pattern)

# ==================================================================================================
@router.get("/by-puuid/{puuid}", response_model=list[str], tags=[SRC_ROUTE])
async def ListMatchesByPuuid(
        response: Response,
        puuid: str,
        startTime: int | None = None,
        endTime: int | None = None,
        queue: int | None = None,
        type: str | None = None,
        start: Annotated[int, Query(ge=0)] | None = 0,
        count: Annotated[int, Query(ge=0, le=100)] | None = 20,
        continent: Annotated[str | None, Query(pattern=MATCH_CONTINENT_ANNOTATED_PATTERN)] = None,
) -> list[str]:
    f"""
    {MatchV5_Endpoints.ListMatchesByPuuid}
    List match ids of a player by puuid.

    Arguments:
    ---------

    - path::continent (str)
        The continent of the player.

    - path::puuid (str)
        The puuid of the player.

    - query::startTime (str)
        Epoch timestamp in seconds. The matchlist started storing timestamps on June 16th, 2021. Any matches 
        played before June 16th, 2021 won't be included in the results if the startTime filter is set.
    
    - query::endTime (str)
        Epoch timestamp in seconds.
        
    - query::queue (int)
        Filter the list of match ids by a specific queue id. This filter is mutually inclusive of the 'type' filter 
        meaning any match ids returned must match both the queue and type filters.
    
    - query::type (str)
        Filter the list of match ids by the type of match. This filter is mutually inclusive of the 'queue' filter 
        meaning any match ids returned must match both the queue and type filters.
    
    - query::start (int)
        The starting index of the match ids to return. Default is 0. Zero means the latest match the player's play.
        
    - query::count (int)
        The number of match ids to return. Default is 20. The maximum number of matches returned is 100.

    """
    httpx_response = await _ListMatchesByPuuid(puuid=puuid, continent=continent,
                                               pattern=MATCH_CONTINENT_ANNOTATED_PATTERN, startTime=startTime,
                                               endTime=endTime, queue=queue, type=type, start=start, count=count)
    PassToStarletteResponse(httpx_response, response)
    return httpx_response.json()


@router.get("/{matchId}", response_model=MatchDto, tags=[SRC_ROUTE])
async def GetMatch(
        response: Response,
        matchId: str,
        continent: Annotated[str | None, Query(pattern=MATCH_CONTINENT_ANNOTATED_PATTERN)] = None,
) -> MatchDto:
    f"""
    {MatchV5_Endpoints.GetMatchById}
    Get match information by match id.

    Arguments:
    ---------

    - query::continent (str)
        The continent of the player.

    - path::matchId (str)
        The match's ID.

    """
    httpx_response = await _GetMatch(matchId=matchId, continent=continent, pattern=MATCH_CONTINENT_ANNOTATED_PATTERN)
    PassToStarletteResponse(httpx_response, response)
    return httpx_response.json()


@router.get("/{matchId}/timeline", response_model=TimeLineDto, tags=[SRC_ROUTE])
async def GetMatchTimeline(
        response: Response,
        matchId: str,
        continent: Annotated[str | None, Query(pattern=MATCH_CONTINENT_ANNOTATED_PATTERN)] = None,
) -> TimeLineDto:
    f"""
    {MatchV5_Endpoints.GetMatchTimelineById}
    Get match timeline by match id.

    Arguments:
    ---------

    - query::continent (str)
        The continent of the player.

    - path::matchId (str)
        The match's ID.

    """
    httpx_response = await _GetMatchTimeline(matchId=matchId, continent=continent,
                                             pattern=MATCH_CONTINENT_ANNOTATED_PATTERN)
    PassToStarletteResponse(httpx_response, response)
    return httpx_response.json()


