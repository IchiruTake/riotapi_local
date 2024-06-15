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
from src.backend.riotapi.routes._endpoints import LeagueExpV4_Endpoints
from src.backend.riotapi.models.LeagueExpV4 import LeagueEntryDTO


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
async def _GetLeagueEntries(queue: str, tier: str, division: str, region: str | None, pattern: str,
                            page: int | None = 1) -> HttpxResponse:
    path_endpoint: str = LeagueExpV4_Endpoints.GetLeagueEntries.format(queue=queue, tier=tier, division=division)
    ops = [('page', page)]
    params = {key: value for key, value in ops if value is not None}
    return await QueryToRiotAPI(host=region, credentials=_CREDENTIALS, endpoint=path_endpoint, router=router,
                                method="GET", params=params, headers=None, cookies=None, usr_response=None,
                                host_pattern=pattern)


# ==================================================================================================
_QUEUE_LIST = ["RANKED_SOLO_5x5", "RANKED_TFT", "RANKED_FLEX_SR", "RANKED_FLEX_TFT"]
_TIER_LIST = ["CHALLENGER", "GRANDMASTER", "MASTER", "DIAMOND", "EMERALD", "PLATINUM", "GOLD", "SILVER",
              "BRONZE", "IRON"]
_DIVISION_LIST = ["I", "II", "III", "IV"]

_QUEUE_PATTERN = "|".join(_QUEUE_LIST)
_TIER_PATTERN = "|".join(_TIER_LIST)
_DIVISION_PATTERN = "|".join(_DIVISION_LIST)

@router.get("/{queue}/{tier}/{division}", response_model=list[LeagueEntryDTO], tags=[SRC_ROUTE])
async def GetLeagueEntries(
        response: Response,
        queue: Annotated[str, Path(title="queue", pattern=_QUEUE_PATTERN)] = "RANKED_SOLO_5x5",
        tier: Annotated[str, Path(title="tier", pattern=_TIER_PATTERN)] = "PLATINUM",
        division: Annotated[str, Path(title="division", pattern=_DIVISION_PATTERN)] = "I",
        page: Annotated[int | None, Query(ge=1)] = 1,
        region: Annotated[str | None, Query(pattern=MATCH_CONTINENT_ANNOTATED_PATTERN)] = None,
) -> list[LeagueEntryDTO]:
    f"""
    {LeagueExpV4_Endpoints.GetLeagueEntries}
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

