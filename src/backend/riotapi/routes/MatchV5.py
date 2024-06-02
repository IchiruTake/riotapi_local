"""
See here for updates:
https://github.com/RiotGames/developer-relations/issues/928

"""


from time import perf_counter
from typing import Annotated

from cachetools.func import ttl_cache
from fastapi import Query
from fastapi.routing import APIRouter

from src.backend.riotapi.routes._region import REGION_ANNOTATED_PATTERN, GetRiotClientByUserRegion, \
    QueryToRiotAPI
from src.utils.static import BASE_TTL_ENTRY, BASE_TTL_DURATION
from src.backend.riotapi.routes._endpoints import MatchV5_Endpoints
from src.backend.riotapi.models.MatchV5 import MatchDto


router = APIRouter()
SRC_ROUTE: str = str(__name__).split('.')[-1]


@ttl_cache(maxsize=BASE_TTL_ENTRY, ttl=BASE_TTL_DURATION, timer=perf_counter, typed=True)
@router.get("/by-puuid/{puuid}", response_model=list[str], tags=[SRC_ROUTE])
async def ListMatches(
        region: Annotated[str, Query(pattern=REGION_ANNOTATED_PATTERN)],
        puuid: str,
        startTime: int | None = None,
        endTime: int | None = None,
        queue: int | None = None,
        type: str | None = None,
        start: Annotated[int, Query(default=20, ge=0)] | None = 0,
        count: Annotated[int, Query(default=20, ge=0, le=100)] | None = 20,
    ) -> list[str]:
    f"""
    {MatchV5_Endpoints.ListMatchesByPuuid}
    List match ids of a player by puuid.

    Arguments:
    ---------

    - path::region (str)
        The region of the player.

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
    client = GetRiotClientByUserRegion(region, src_route=SRC_ROUTE, router=router,
                                       bypass_region_route=False)
    endpoint: str = MatchV5_Endpoints.ListMatchesByPuuid.format(puuid=puuid)

    ops = [('startTime', startTime), ('endTime', endTime), ('queue', queue), ('type', type), ('start', start),
           ('count', count)]
    params = {key: value for key, value in ops if value is not None}
    return await QueryToRiotAPI(client, endpoint, params=params)


@ttl_cache(maxsize=BASE_TTL_ENTRY, ttl=BASE_TTL_DURATION, timer=perf_counter, typed=True)
@router.get("/{matchId}", response_model=MatchDto, tags=[SRC_ROUTE])
async def GetMatch(
        matchId: str,
        region: Annotated[str, Query(pattern=REGION_ANNOTATED_PATTERN)]
) -> MatchDto:
    f"""
    {MatchV5_Endpoints.ListMatchesByPuuid}
    List match ids of a player by puuid.

    Arguments:
    ---------

    - path::region (str)
        The region of the player.

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
    client = GetRiotClientByUserRegion(region, src_route=SRC_ROUTE, router=router,
                                       bypass_region_route=False)
    endpoint: str = MatchV5_Endpoints.GetMatchById.format(matchId=matchId)
    return await QueryToRiotAPI(client, endpoint)
