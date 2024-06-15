"""
See here for updates:
https://github.com/RiotGames/developer-relations/issues/928

"""

from time import perf_counter
from typing import Annotated

from cachetools.func import ttl_cache
from fastapi import Query, Path
from src.backend.riotapi.inapp import CustomAPIRouter
from fastapi.responses import Response
from httpx import Response as HttpxResponse

from src.backend.riotapi.routes._query import QueryToRiotAPI, PassToStarletteResponse
from src.static.static import BASE_TTL_ENTRY, BASE_TTL_DURATION, CREDENTIALS, MATCH_CONTINENT_ANNOTATED_PATTERN
from src.backend.riotapi.routes._endpoints import LeagueV4_Endpoints
from src.backend.riotapi.models.LeagueV4 import LeagueEntryDTO, LeagueItemDTO, LeagueListDTO
from src.backend.riotapi.routes.LeagueExpV4 import GetLeagueEntries


# ==================================================================================================
_CREDENTIALS = [CREDENTIALS.LOL, CREDENTIALS.FULL]
router = CustomAPIRouter()
SRC_ROUTE: str = str(__name__).split('.')[-1]
router.load_profile(name=f"riotapi.routers.{SRC_ROUTE}")


# ==================================================================================================
# Enable Server Caching
MAXSIZE1, TTL1 = router.scale(maxsize=BASE_TTL_ENTRY, ttl=BASE_TTL_DURATION, region_path=False, num_params=1)
MAXSIZE2, TTL2 = router.scale(maxsize=BASE_TTL_ENTRY, ttl=BASE_TTL_DURATION, region_path=False, num_params=2)
MAXSIZE3, TTL3 = router.scale(maxsize=BASE_TTL_ENTRY, ttl=BASE_TTL_DURATION, region_path=False, num_params=3)


@ttl_cache(maxsize=MAXSIZE3, ttl=TTL3, timer=perf_counter, typed=True)
async def _GetLeagueEntriesByRank(queue: str, tier: str, region: str | None, pattern: str) -> HttpxResponse:
    match tier:
        case "CHALLENGER":
            path_endpoint = LeagueV4_Endpoints.GetChallengerLeague.format(queue=queue)
        case "GRANDMASTER":
            path_endpoint = LeagueV4_Endpoints.GetGrandmasterLeague.format(queue=queue)
        case "MASTER":
            path_endpoint = LeagueV4_Endpoints.GetMasterLeague.format(queue=queue)
        case _:
            raise ValueError(f"Invalid queue type: {queue}")
    return await QueryToRiotAPI(host=region, credentials=_CREDENTIALS, endpoint=path_endpoint, router=router,
                                method="GET", params=None, headers=None, cookies=None, usr_response=None,
                                host_pattern=pattern)

@ttl_cache(maxsize=MAXSIZE3, ttl=TTL3, timer=perf_counter, typed=True)
async def _GetLeagueEntries(queue: str, tier: str, division: str, region: str | None, pattern: str,
                            page: int | None = 1) -> HttpxResponse:
    path_endpoint: str = LeagueV4_Endpoints.GetLeagueEntries.format(queue=queue, tier=tier, division=division)
    ops = [('page', page)]
    params = {key: value for key, value in ops if value is not None}
    return await QueryToRiotAPI(host=region, credentials=_CREDENTIALS, endpoint=path_endpoint, router=router,
                                method="GET", params=params, headers=None, cookies=None, usr_response=None,
                                host_pattern=pattern)

@ttl_cache(maxsize=MAXSIZE1, ttl=TTL1, timer=perf_counter, typed=True)
async def _GetLeagueEntriesBySummonerId(summonerId: str, region: str | None, pattern: str) -> HttpxResponse:
    path_endpoint: str = LeagueV4_Endpoints.GetLeagueEntriesBySummonerID.format(summonerId=summonerId)
    return await QueryToRiotAPI(host=region, credentials=_CREDENTIALS, endpoint=path_endpoint, router=router,
                                method="GET", params=None, headers=None, cookies=None, usr_response=None,
                                host_pattern=pattern)


# ==================================================================================================
_QUEUE1_LIST = ["RANKED_SOLO_5x5", "RANKED_FLEX_SR", "RANKED_FLEX_TFT"]
_TIER1_LIST = ["CHALLENGER", "GRANDMASTER", "MASTER"]
_QUEUE1_PATTERN = "|".join(_QUEUE1_LIST)
_TIER1_PATTERN = "|".join(_TIER1_LIST)


@router.get("/{queue}/{tier}", response_model=LeagueListDTO, tags=[SRC_ROUTE])
async def GetLeagueEntriesByRank(
        response: Response,
        queue: Annotated[str, Path(title="queue", pattern=_QUEUE1_PATTERN)] = "RANKED_SOLO_5x5",
        tier: Annotated[str, Path(title="tier", pattern=_TIER1_PATTERN)] = "CHALLENGER",
        region: Annotated[str | None, Query(pattern=MATCH_CONTINENT_ANNOTATED_PATTERN)] = None,
) -> LeagueListDTO:
    f"""
    CHALLENGER: {LeagueV4_Endpoints.GetChallengerLeague}
    GRANDMASTER: {LeagueV4_Endpoints.GetGrandmasterLeague}
    MASTER: {LeagueV4_Endpoints.GetMasterLeague}
    Get the challenger league for given queue type.

    Arguments:
    ---------

    - path::queue (str)
        The queue type of the league. Allowed values: RANKED_SOLO_5x5, RANKED_FLEX_SR, RANKED_FLEX_TFT
        Default: RANKED_SOLO_5x5

    - path::tier (str)
        The tier of the league. Allowed values: CHALLENGER, GRANDMASTER, MASTER. Default: CHALLENGER

    - query::region (str)
        The region of the player. 

    """
    httpx_response = await _GetLeagueEntriesByRank(queue=queue, tier=tier, region=region,
                                                   pattern=MATCH_CONTINENT_ANNOTATED_PATTERN)
    PassToStarletteResponse(httpx_response, response)
    return httpx_response.json()


_QUEUE2_LIST = ["RANKED_SOLO_5x5", "RANKED_TFT", "RANKED_FLEX_SR", "RANKED_FLEX_TFT"]
_TIER2_LIST = ["CHALLENGER", "GRANDMASTER", "MASTER", "DIAMOND", "EMERALD", "PLATINUM", "GOLD", "SILVER",
               "BRONZE", "IRON"]
_DIVISION2_LIST = ["I", "II", "III", "IV"]

_QUEUE2_PATTERN = "|".join(_QUEUE2_LIST)
_TIER2_PATTERN = "|".join(_TIER2_LIST)
_DIVISION2_PATTERN = "|".join(_DIVISION2_LIST)

@router.get("/{queue}/{tier}/{division}", response_model=list[LeagueEntryDTO], tags=[SRC_ROUTE])
async def GetLeagueEntries(
        response: Response,
        queue: Annotated[str, Path(title="queue", pattern=_QUEUE2_PATTERN)] = "RANKED_SOLO_5x5",
        tier: Annotated[str, Path(title="tier", pattern=_TIER2_PATTERN)] = "PLATINUM",
        division: Annotated[str, Path(title="division", pattern=_DIVISION2_PATTERN)] = "I",
        page: Annotated[int | None, Query(ge=1)] = 1,
        region: Annotated[str | None, Query(pattern=MATCH_CONTINENT_ANNOTATED_PATTERN)] = None,
) -> list[LeagueEntryDTO]:
    f"""
    {LeagueV4_Endpoints.GetLeagueEntries}
    Get all the league entries

    Arguments:
    ---------

    - path::queue (str)
        The queue type of the league. Allowed values: RANKED_SOLO_5x5, RANKED_TFT, RANKED_FLEX_SR, RANKED_FLEX_TFT
        Default: RANKED_SOLO_5x5

    - path::tier (str)
        The tier of the league. Allowed values: CHALLENGER, GRANDMASTER, MASTER, DIAMOND, EMERALD, PLATINUM, GOLD, 
        SILVER, BRONZE, IRON. Default: PLATINUM

    - path::division (str)
        The division of the league. Allowed values: I, II, III, IV. Default: I

    - query::page (int)
        The page number of the league entries. Default: 1

    - query::region (str)
        The region of the player. 

    """
    httpx_response = await _GetLeagueEntries(queue=queue, tier=tier, division=division, region=region,
                                             pattern=MATCH_CONTINENT_ANNOTATED_PATTERN, page=page)
    PassToStarletteResponse(httpx_response, response)
    return httpx_response.json()


@router.get("/by-summoner/{summonerId}", response_model=list[LeagueEntryDTO], tags=[SRC_ROUTE])
async def GetLeagueEntriesBySummonerId(
        response: Response,
        summonerId: str,
        region: Annotated[str | None, Query(pattern=MATCH_CONTINENT_ANNOTATED_PATTERN)] = None,
) -> list[LeagueEntryDTO]:
    f"""
    {LeagueV4_Endpoints.GetLeagueEntriesBySummonerID}
    Get the league entries by summoner id

    Arguments:
    ---------
    
    - path::summonerId (str)
        The summoner id of the player.
        
    - query::region (str)
        The region of the player. 

    """
    httpx_response = await _GetLeagueEntriesBySummonerId(summonerId=summonerId, region=region,
                                                         pattern=MATCH_CONTINENT_ANNOTATED_PATTERN)
    PassToStarletteResponse(httpx_response, response)
    return httpx_response.json()