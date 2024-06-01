from time import perf_counter
from typing import Callable, Sequence, Annotated

from cachetools.func import ttl_cache
from fastapi import Path
from fastapi.exceptions import HTTPException
from fastapi.routing import APIRouter
from pydantic import BaseModel, Field

from src.backend.riotapi.routes._region import GetRiotClientByUserRegion, QueryToRiotAPI, \
    REGION_ANNOTATED_PATTERN
from src.utils.static import BASE_TTL_ENTRY, BASE_TTL_DURATION, BASE_TTL_MULTIPLIER


# ==================================================================================================
class ChampionMasteryV4_Endpoints:
    MasteryByPuuid: str = '/lol/champion-mastery/v4/champion-masteries/by-puuid/{puuid}'
    MasteryByPuuidAndChampionID: str = \
        '/lol/champion-mastery/v4/champion-masteries/by-puuid/{puuid}/by-champion/{championId}'
    TopMasteryByPuuid: str = '/lol/champion-mastery/v4/champion-masteries/by-puuid/{puuid}/top'
    MasteryScoreByPuuid: str = '/lol/champion-mastery/v4/scores/by-puuid/{puuid}'


class ChampionMasteryDto(BaseModel):
    puuid: str = Field(..., title="PUUID", description="The PUUID of the player you want to track", max_length=78,
                       frozen=True)
    championId: int = Field(..., description="Champion ID for this entry.")
    championLevel: int = Field(..., description="Champion level for specified player and champion combination.")
    championPoints: int = Field(...,
                                description="Total number of champion points for this player and champion combination "
                                            "- they are used to determine championLevel.")
    lastPlayTime: int = Field(..., description="Last time this champion was played by this player - in Unix "
                                               "seconds time format.")
    championPointsSinceLastLevel: int = Field(..., description="Number of points earned since current level "
                                                               "has been achieved.")
    championPointsUntilNextLevel: int = Field(...,
                                              description="Number of points needed to achieve next level. Zero if "
                                                          "player reached maximum champion level for this champion.")
    chestGranted: bool = Field(..., description="Is chest granted for this champion or not in current season.")
    tokensEarned: int = Field(..., description="The token earned for this champion at the current championLevel. "
                                               "When the championLevel is advanced the tokensEarned resets to 0.")
    summonerId: str = Field(..., description="Summoner ID for this entry. (Encrypted)", frozen=True)


# ==================================================================================================
router = APIRouter()
SRC_ROUTE = str(__name__).split('.')[-1]

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
        region: Annotated[str, Path(pattern=REGION_ANNOTATED_PATTERN)]
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
    client = GetRiotClientByUserRegion(region, src_route=str(__name__), router=router,
                                       bypass_region_route=True)
    path_endpoint: str = ChampionMasteryV4_Endpoints.MasteryByPuuid.format(puuid=puuid)
    return await QueryToRiotAPI(client, path_endpoint)


@_ProcessChampionMastery
@ttl_cache(maxsize=BASE_TTL_ENTRY * BASE_TTL_MULTIPLIER, ttl=BASE_TTL_DURATION, timer=perf_counter, typed=True)
@router.get("/{region}/{puuid}/{championId}", response_model=ChampionMasteryDto, tags=[SRC_ROUTE])
async def GetChampionMastery(
        puuid: str,
        championId: int,
        region: Annotated[str, Path(pattern=REGION_ANNOTATED_PATTERN)],
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
    champion_masteries = await ListChampionMastery(puuid, region)
    for mastery in champion_masteries:
        if mastery.championId == championId:
            return mastery
    raise HTTPException(status_code=404, detail="Champion mastery is not found")


@_ProcessChampionMastery
@ttl_cache(maxsize=BASE_TTL_ENTRY * BASE_TTL_MULTIPLIER, ttl=BASE_TTL_DURATION, timer=perf_counter, typed=True)
@router.get("/{region}/{puuid}/top{count}", response_model=list[ChampionMasteryDto], tags=[SRC_ROUTE])
async def ListTopChampionMastery(
        puuid: str,
        region: Annotated[str, Path(pattern=REGION_ANNOTATED_PATTERN)],
        count: int = 3
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
    if count < 1:
        raise HTTPException(status_code=400, detail="Invalid count")
    return await ListChampionMastery(puuid, region)[:count]


@ttl_cache(maxsize=BASE_TTL_ENTRY, ttl=BASE_TTL_DURATION, timer=perf_counter, typed=True)
@router.get("/{region}/{puuid}/score", response_model=int, tags=[SRC_ROUTE])
async def GetChampionMasteryScore(
        puuid: str,
        region: Annotated[str, Path(pattern=REGION_ANNOTATED_PATTERN)]
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
    client = GetRiotClientByUserRegion(region, src_route="ChampionMasteryV4", router=router,
                                       bypass_region_route=True)
    path_endpoint: str = ChampionMasteryV4_Endpoints.MasteryScoreByPuuid.format(puuid=puuid)
    return await QueryToRiotAPI(client, path_endpoint)
