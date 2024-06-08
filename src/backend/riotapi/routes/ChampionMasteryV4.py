from time import perf_counter
from typing import Callable, Sequence, Annotated

from cachetools.func import ttl_cache
from fastapi import Path
from fastapi.responses import Response
from fastapi.exceptions import HTTPException
from fastapi.routing import APIRouter
from starlette.status import HTTP_404_NOT_FOUND, HTTP_400_BAD_REQUEST

from src.backend.riotapi.routes._query import QueryToRiotAPI
from src.static.static import (BASE_TTL_ENTRY, BASE_TTL_DURATION, BASE_TTL_MULTIPLIER, REGION_ANNOTATED_PATTERN,
                               CREDENTIALS)
from src.backend.riotapi.models.ChampionMasteryV4 import ChampionMasteryDto
from src.backend.riotapi.routes._endpoints import ChampionMasteryV4_Endpoints

# ==================================================================================================
router = APIRouter()
SRC_ROUTE = str(__name__).split('.')[-1]
_CREDENTIALS = [CREDENTIALS.LOL, CREDENTIALS.FULL]


def _ProcessChampionMastery(func: Callable):
    def wrapper(*args, **kwargs) -> list[ChampionMasteryDto] | ChampionMasteryDto:
        output: list[ChampionMasteryDto] | ChampionMasteryDto = func(*args, **kwargs)
        if isinstance(output, ChampionMasteryDto):
            output.lastPlayTime = output.lastPlayTime // 1000
        elif isinstance(output, Sequence):
            for mastery in output:
                mastery.lastPlayTime = mastery.lastPlayTime // 1000
            if isinstance(output, list):
                output.sort(key=lambda x: x.championPoints, reverse=True)
        return output

    return wrapper


# ==================================================================================================
@_ProcessChampionMastery
@ttl_cache(maxsize=BASE_TTL_ENTRY, ttl=BASE_TTL_DURATION, timer=perf_counter, typed=True)
@router.get("/{region}/{puuid}", response_model=list[ChampionMasteryDto], tags=[SRC_ROUTE])
async def ListChampionMastery(
        puuid: str,
        response: Response,
        region: Annotated[str | None, Path(pattern=REGION_ANNOTATED_PATTERN)] = None,
) -> list[ChampionMasteryDto]:
    f"""
    {ChampionMasteryV4_Endpoints.MasteryByPuuid}
    List all champion mastery entries sorted by number of champion points descending. 

    Arguments:
    ---------

    - path::puuid (str)
        The puuid of the player.

    - path::region (str)
        The region of the player.

    """
    path_endpoint: str = ChampionMasteryV4_Endpoints.MasteryByPuuid.format(puuid=puuid)
    return await QueryToRiotAPI(host=region, credentials=_CREDENTIALS, endpoint=path_endpoint, router=router,
                                method="GET", params=None, headers=None, cookies=None, usr_response=response)


@_ProcessChampionMastery
@ttl_cache(maxsize=BASE_TTL_ENTRY * BASE_TTL_MULTIPLIER, ttl=BASE_TTL_DURATION, timer=perf_counter, typed=True)
@router.get("/{region}/{puuid}/{championId}", response_model=ChampionMasteryDto, tags=[SRC_ROUTE])
async def GetChampionMastery(
        puuid: str,
        championId: int,
        response: Response,
        region: Annotated[str | None, Path(pattern=REGION_ANNOTATED_PATTERN)] = None,
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

    - path::region (str)
        The region of the player.

    """
    champion_masteries = await ListChampionMastery(puuid, region, response=response)
    for mastery in champion_masteries:
        if mastery.championId == championId:
            return mastery
    raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Champion mastery is not found")


@_ProcessChampionMastery
@ttl_cache(maxsize=BASE_TTL_ENTRY * BASE_TTL_MULTIPLIER, ttl=BASE_TTL_DURATION, timer=perf_counter, typed=True)
@router.get("/{region}/{puuid}/top{count}", response_model=list[ChampionMasteryDto], tags=[SRC_ROUTE])
async def ListTopChampionMastery(
        puuid: str,
        response: Response,
        region: Annotated[str | None, Path(pattern=REGION_ANNOTATED_PATTERN)] = None,
        count: Annotated[int, Path(ge=1)] = 3
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

    - path::region (str)
        The region of the player.

    """
    return await ListChampionMastery(puuid, region, response=response)[:count]


@ttl_cache(maxsize=BASE_TTL_ENTRY, ttl=BASE_TTL_DURATION, timer=perf_counter, typed=True)
@router.get("/{region}/{puuid}/score", response_model=int, tags=[SRC_ROUTE])
async def GetChampionMasteryScore(
        puuid: str,
        response: Response,
        region: Annotated[str | None, Path(pattern=REGION_ANNOTATED_PATTERN)] = None,
) -> int:
    f"""
    {ChampionMasteryV4_Endpoints.MasteryScoreByPuuid}
    Get a player's total champion mastery score, which is the sum of individual champion mastery levels.

    Arguments:
    ---------

    - path::puuid (str)
        The puuid of the player.

    - path::region (str)
        The region of the player.

    """
    path_endpoint: str = ChampionMasteryV4_Endpoints.MasteryScoreByPuuid.format(puuid=puuid)
    return await QueryToRiotAPI(host=region, credentials=_CREDENTIALS, endpoint=path_endpoint, router=router,
                                method="GET", params=None, headers=None, cookies=None, usr_response=response)
