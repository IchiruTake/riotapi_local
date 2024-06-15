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
from src.backend.riotapi.routes._endpoints import LolStatusV4_Endpoints
from src.backend.riotapi.models.LolStatusV4 import PlatformDataDto


# ==================================================================================================
_CREDENTIALS = [CREDENTIALS.LOL, CREDENTIALS.FULL]
router = CustomAPIRouter()
SRC_ROUTE: str = str(__name__).split('.')[-1]
router.load_profile(name=f"riotapi.routers.{SRC_ROUTE}")


# ==================================================================================================
# Enable Server Caching
MAXSIZE1, TTL1 = router.scale(maxsize=BASE_TTL_ENTRY, ttl=BASE_TTL_DURATION, region_path=False, num_params=1)
MAXSIZE2, TTL2 = router.scale(maxsize=BASE_TTL_ENTRY, ttl=BASE_TTL_DURATION, region_path=False, num_params=2)


@ttl_cache(maxsize=MAXSIZE1, ttl=TTL1, timer=perf_counter, typed=True)
async def _GetPlatformData(region: str | None, pattern: str) -> HttpxResponse:
    path_endpoint: str = LolStatusV4_Endpoints.GetPlatformData.format()
    return await QueryToRiotAPI(host=region, credentials=_CREDENTIALS, endpoint=path_endpoint, router=router,
                                method="GET", params=None, headers=None, cookies=None, usr_response=None,
                                host_pattern=pattern)


# ==================================================================================================
@router.get("/{queue}/{tier}/{division}", response_model=PlatformDataDto, tags=[SRC_ROUTE])
async def GetPlatformData(
        response: Response,
        region: Annotated[str | None, Query(pattern=MATCH_CONTINENT_ANNOTATED_PATTERN)] = None,
) -> PlatformDataDto:
    f"""
    {LolStatusV4_Endpoints.GetPlatformData}
    Get League of Legends status for the given platform

    Arguments:
    ---------

    - query::region (str)
        The region of the player. 

    """
    httpx_response = await _GetPlatformData(region=region, pattern=MATCH_CONTINENT_ANNOTATED_PATTERN)
    PassToStarletteResponse(httpx_response, response)
    return httpx_response.json()

