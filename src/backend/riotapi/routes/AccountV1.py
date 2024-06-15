from time import perf_counter
from typing import Annotated

from cachetools.func import ttl_cache
from fastapi import Path, Query, Response
from httpx import Response as HttpxResponse

from src.backend.riotapi.inapp import CustomAPIRouter
from src.backend.riotapi.models.AccountV1 import AccountDto, ActiveShardDto
from src.backend.riotapi.routes._endpoints import AccountV1_Endpoints
from src.backend.riotapi.routes._query import QueryToRiotAPI, PassToStarletteResponse
from src.static.static import (BASE_TTL_ENTRY, BASE_TTL_DURATION, NORMAL_CONTINENT_ANNOTATED_PATTERN, CREDENTIALS)

# ==================================================================================================
_CREDENTIALS = [CREDENTIALS.LOL, CREDENTIALS.LOR, CREDENTIALS.TFT, CREDENTIALS.VAL, CREDENTIALS.FULL]
router = CustomAPIRouter()
SRC_ROUTE: str = str(__name__).split('.')[-1]
router.load_profile(name=f"riotapi.routers.{SRC_ROUTE}")

# ==================================================================================================
# Enable Server Caching
MAXSIZE1, TTL1 = router.scale(maxsize=BASE_TTL_ENTRY, ttl=BASE_TTL_DURATION, region_path=False, num_params=1)
MAXSIZE2, TTL2 = router.scale(maxsize=BASE_TTL_ENTRY, ttl=BASE_TTL_DURATION, region_path=False, num_params=2)


@ttl_cache(maxsize=MAXSIZE2, ttl=TTL2, timer=perf_counter, typed=True)
async def _GetAccountByRiotId(username: str, tagLine: str, continent: str | None, pattern: str) -> HttpxResponse:
    path_endpoint: str = AccountV1_Endpoints.AccountByRiotId.format(userName=username, tagLine=tagLine)
    return await QueryToRiotAPI(host=continent, credentials=_CREDENTIALS, endpoint=path_endpoint, router=router,
                                method="GET", params=None, headers=None, cookies=None, usr_response=None,
                                host_pattern=pattern)


@ttl_cache(maxsize=MAXSIZE1, ttl=TTL1, timer=perf_counter, typed=True)
async def _GetAccountByPuuid(puuid: str, continent: str | None, pattern: str) -> HttpxResponse:
    path_endpoint: str = AccountV1_Endpoints.AccountByPuuid.format(puuid=puuid)
    return await QueryToRiotAPI(host=continent, credentials=_CREDENTIALS, endpoint=path_endpoint, router=router,
                                method="GET", params=None, headers=None, cookies=None, usr_response=None,
                                host_pattern=pattern)


@ttl_cache(maxsize=MAXSIZE1, ttl=TTL1, timer=perf_counter, typed=True)
async def _GetActiveShardForPlayer(game: str, puuid: str, continent: str | None, pattern: str) -> HttpxResponse:
    path_endpoint: str = AccountV1_Endpoints.ActiveShardForPlayer.format(game=game, puuid=puuid)
    return await QueryToRiotAPI(host=continent, credentials=_CREDENTIALS, endpoint=path_endpoint, router=router,
                                method="GET", params=None, headers=None, cookies=None, usr_response=None,
                                host_pattern=pattern)


# ==================================================================================================
@router.get("/by-riot-id/{username}/{tagLine}", response_model=AccountDto, tags=[SRC_ROUTE])
async def GetAccountByRiotId(
        response: Response,
        username: str, tagLine: str,
        continent: Annotated[str | None, Query(pattern=NORMAL_CONTINENT_ANNOTATED_PATTERN)] = None,
) -> AccountDto:
    f"""
    {AccountV1_Endpoints.AccountByRiotId}
    Get the Riot account information of a player by their username and tagline.

    Arguments:
    ---------

    - path::username (str)
        The username of the player.

    - path::tagLine (str)
        The tagline of the player.

    - query::continent (str)
        The continent of the player.

    """
    httpx_response = await _GetAccountByRiotId(username=username, tagLine=tagLine, continent=continent,
                                                              pattern=NORMAL_CONTINENT_ANNOTATED_PATTERN)
    PassToStarletteResponse(httpx_response, response)
    return httpx_response.json()


@router.get("/by-puuid/{puuid}", response_model=AccountDto, tags=[SRC_ROUTE])
async def GetAccountByPuuid(
        response: Response,
        puuid: str,
        continent: Annotated[str | None, Query(pattern=NORMAL_CONTINENT_ANNOTATED_PATTERN)] = None,
) -> AccountDto:
    f"""
    {AccountV1_Endpoints.AccountByPuuid}
    Get the Riot account information of a player by their puuid

    Arguments:
    ---------

    - path::continent (str)
        The puuid of the player.

    - query::continent (str)
        The continent of the player.

    """
    httpx_response = await _GetAccountByPuuid(puuid=puuid, continent=continent,
                                                             pattern=NORMAL_CONTINENT_ANNOTATED_PATTERN)
    PassToStarletteResponse(httpx_response, response)
    return httpx_response.json()


@ttl_cache(maxsize=BASE_TTL_ENTRY, ttl=BASE_TTL_DURATION, timer=perf_counter, typed=True)
@router.get("/by-game/{game}/{puuid}", response_model=ActiveShardDto, tags=[SRC_ROUTE])
async def GetActiveShardForPlayer(
        response: Response,
        puuid: str,
        game: Annotated[str, Path(pattern="val|lor")],
        continent: Annotated[str | None, Query(pattern=NORMAL_CONTINENT_ANNOTATED_PATTERN)] = None,
) -> ActiveShardDto:
    f"""
    {AccountV1_Endpoints.ActiveShardForPlayer}
    Get the Riot active shard of a player by their puuid

    Arguments:
    ---------

    - path::game (str)
        The game of the player. Supported values are 'val' (Valorant) and 'lor' (League of Runeterra).

    - path::puuid (str)
        The puuid of the player.

    - query::continent (str)
        The continent of the player.

    """
    httpx_response = await _GetActiveShardForPlayer(game=game, puuid=puuid, continent=continent,
                                                                   pattern=NORMAL_CONTINENT_ANNOTATED_PATTERN)
    PassToStarletteResponse(httpx_response, response)
    return httpx_response.json()
