from time import perf_counter
from typing import Callable, Sequence, Annotated

from cachetools.func import ttl_cache
from fastapi import Query, Path
from fastapi.responses import Response
from fastapi.exceptions import HTTPException
from src.backend.riotapi.inapp import CustomAPIRouter
from starlette.status import HTTP_404_NOT_FOUND

from src.backend.riotapi.routes._query import QueryToRiotAPI, PassToStarletteResponse
from src.static.static import (BASE_TTL_ENTRY, BASE_TTL_DURATION, BASE_TTL_MULTIPLIER, REGION_ANNOTATED_PATTERN,
                               CREDENTIALS)
from src.backend.riotapi.models.ChampionMasteryV4 import ChampionMasteryDto
from src.backend.riotapi.routes._endpoints import ChampionMasteryV4_Endpoints
from httpx import Response as HttpxResponse


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
async def _ListChampionMastery(puuid: str, region: str | None, pattern: str) \
        -> tuple[HttpxResponse, list[ChampionMasteryDto]]:
    path_endpoint: str = ChampionMasteryV4_Endpoints.MasteryByPuuid.format(puuid=puuid)
    httpx_response = await QueryToRiotAPI(host=region, credentials=_CREDENTIALS, endpoint=path_endpoint, router=router,
                                          method="GET", params=None, headers=None, cookies=None, usr_response=None,
                                          host_pattern=pattern)
    content: list = httpx_response.json()
    if httpx_response.status_code // 100 >= 4:
        return httpx_response, content
    output: list[ChampionMasteryDto] = []
    if not isinstance(content, list):
        mastery = ChampionMasteryDto.parse_obj(content)
        mastery.lastPlayTime = mastery.lastPlayTime // 1000
        output.append(mastery)
    else:
        for ins in content:
            mastery = ChampionMasteryDto.parse_obj(ins)
            mastery.lastPlayTime = mastery.lastPlayTime // 1000
            output.append(mastery)
    return httpx_response, output


@ttl_cache(maxsize=MAXSIZE1, ttl=TTL1, timer=perf_counter, typed=True)
async def _GetChampionMasteryScore(puuid: str, region: str | None, pattern: str) -> HttpxResponse:
    path_endpoint: str = ChampionMasteryV4_Endpoints.MasteryScoreByPuuid.format(puuid=puuid)
    return await QueryToRiotAPI(host=region, credentials=_CREDENTIALS, endpoint=path_endpoint, router=router,
                                method="GET", params=None, headers=None, cookies=None, usr_response=None,
                                host_pattern=pattern)


# ==================================================================================================
@router.get("/{puuid}", response_model=list[ChampionMasteryDto], tags=[SRC_ROUTE])
async def ListChampionMastery(
        response: Response,
        puuid: str,
        region: Annotated[str | None, Query(pattern=REGION_ANNOTATED_PATTERN)] = None,
) -> list[ChampionMasteryDto]:
    f"""
    {ChampionMasteryV4_Endpoints.MasteryByPuuid}
    List all champion mastery entries sorted by number of champion points descending. 

    Arguments:
    ---------

    - path::puuid (str)
        The puuid of the player.

    - query::region (str)
        The region of the player.

    """
    httpx_response, output = await _ListChampionMastery(puuid, region, pattern=REGION_ANNOTATED_PATTERN)
    PassToStarletteResponse(httpx_response, response)
    return output


@router.get("/{puuid}/{championId}", response_model=ChampionMasteryDto, tags=[SRC_ROUTE])
async def GetChampionMastery(
        response: Response,
        puuid: str,
        championId: int,
        region: Annotated[str | None, Query(pattern=REGION_ANNOTATED_PATTERN)] = None,
) -> ChampionMasteryDto:
    f"""
    {ChampionMasteryV4_Endpoints.MasteryByPuuidAndChampionID}
    Get a champion mastery by player ID and champion ID.

    Arguments:
    ---------

    - path::puuid (str)
        The puuid of the player.

    - path::championId (int)
        The champion ID.

    - query::region (str)
        The region of the player.

    """
    httpx_response, champion_masteries = await _ListChampionMastery(puuid, region, pattern=REGION_ANNOTATED_PATTERN)
    PassToStarletteResponse(httpx_response, response)
    for mastery in champion_masteries:
        if mastery.championId == championId:
            return mastery
    raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Champion Mastery is not found")


@router.get("/{puuid}/top/{count}", response_model=list[ChampionMasteryDto], tags=[SRC_ROUTE])
async def ListTopChampionMastery(
        response: Response,
        puuid: str,
        count: Annotated[int, Path(ge=1)] = 3,
        region: Annotated[str | None, Query(pattern=REGION_ANNOTATED_PATTERN)] = None,
) -> list[ChampionMasteryDto]:
    f"""
    {ChampionMasteryV4_Endpoints.TopMasteryByPuuid}
    Get a player's top champion mastery entries sorted by number of champion points descending.

    Arguments:
    ---------

    - path::puuid (str)
        The puuid of the player.
        
    - path::count (int)
        The number of entries to retrieve.

    - query::region (str)
        The region of the player.

    """
    httpx_response, champion_masteries = await _ListChampionMastery(puuid, region, pattern=REGION_ANNOTATED_PATTERN)
    PassToStarletteResponse(httpx_response, response)
    return champion_masteries[:min(count, len(champion_masteries))]


@router.get("/{puuid}/score", response_model=int, tags=[SRC_ROUTE])
async def GetChampionMasteryScore(
        puuid: str,
        response: Response,
        region: Annotated[str | None, Query(pattern=REGION_ANNOTATED_PATTERN)] = None,
) -> int:
    f"""
    {ChampionMasteryV4_Endpoints.MasteryScoreByPuuid}
    Get a player's total champion mastery score, which is the sum of individual champion mastery levels.

    Arguments:
    ---------

    - path::puuid (str)
        The puuid of the player.

    - query::region (str)
        The region of the player.

    """
    httpx_response = await _GetChampionMasteryScore(puuid, region, pattern=REGION_ANNOTATED_PATTERN)
    PassToStarletteResponse(httpx_response, response)
    return httpx_response.json()
