from time import perf_counter
from typing import Annotated

from cachetools.func import ttl_cache
from fastapi import Path, Query
from fastapi.routing import APIRouter
from pydantic import BaseModel, Field

from src.backend.riotapi.routes._region import GetRiotClientByUserRegion, QueryToRiotAPI, \
    REGION_ANNOTATED_PATTERN
from src.utils.static import BASE_TTL_ENTRY, BASE_TTL_DURATION


# ==================================================================================================
class AccountV1_Endpoints:
    AccountByPuuid: str = '/riot/account/v1/accounts/by-puuid/{puuid}'
    AccountByRiotId: str = '/riot/account/v1/accounts/by-riot-id/{userName}/{tagLine}'
    ActiveShardForPlayer: str = '/riot/account/v1/active-shards/by-game/{game}/by-puuid/{puuid}'


class AccountDto(BaseModel):
    puuid: str = Field(..., title="PUUID", description="The PUUID of the player you want to track")
    gameName: str = Field(..., title="Player Name", description="The player's name of the player you want to track")
    tagLine: str = Field(..., title="Tagline", description="The tagline of the player you want to track")


class ActiveShardDto(BaseModel):
    puuid: str = Field(..., title="PUUID", description="The PUUID of the player you want to track")
    game: str = Field(..., title="Game", description="The game of the player you want to track")
    ap: str = Field(..., title="Active Shard", description="The active shard of the player you want to track")


# ==================================================================================================
router = APIRouter()
SRC_ROUTE: str = str(__name__).split('.')[-1]


@ttl_cache(maxsize=BASE_TTL_ENTRY, ttl=BASE_TTL_DURATION, timer=perf_counter, typed=True)
@router.get("/by-riot-id/{username}/{tagLine}", response_model=AccountDto, tags=[SRC_ROUTE])
async def GetAccountByRiotId(
        username: str, tagLine: str,
        region: Annotated[str, Query(pattern=REGION_ANNOTATED_PATTERN)]
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

    - query::region (str)
        The region of the player.

    """
    client = GetRiotClientByUserRegion(region, src_route=SRC_ROUTE, router=router)
    path_endpoint: str = AccountV1_Endpoints.AccountByRiotId.format(userName=username, tagLine=tagLine)
    return await QueryToRiotAPI(client, path_endpoint)


@ttl_cache(maxsize=BASE_TTL_ENTRY, ttl=BASE_TTL_DURATION, timer=perf_counter, typed=True)
@router.get("/by-puuid/{puuid}", response_model=AccountDto, tags=[SRC_ROUTE])
async def GetAccountByPuuid(
        puuid: str,
        region: Annotated[str, Query(pattern=REGION_ANNOTATED_PATTERN)]
    ) -> AccountDto:
    f"""
    {AccountV1_Endpoints.AccountByPuuid}
    Get the Riot account information of a player by their puuid

    Arguments:
    ---------

    - path::puuid (str)
        The puuid of the player.

    - query::region (str)
        The region of the player.

    """
    client = GetRiotClientByUserRegion(region, src_route=SRC_ROUTE, router=router)
    path_endpoint: str = AccountV1_Endpoints.AccountByPuuid.format(puuid=puuid)
    return await QueryToRiotAPI(client, path_endpoint)


@ttl_cache(maxsize=BASE_TTL_ENTRY, ttl=BASE_TTL_DURATION, timer=perf_counter, typed=True)
@router.get("/by-game/{game}/{puuid}", response_model=ActiveShardDto, tags=[SRC_ROUTE])
async def GetActiveShardForPlayer(
        game: Annotated[str, Path(pattern="val|lor")],
        puuid: str,
        region: Annotated[str, Query(pattern=REGION_ANNOTATED_PATTERN)]
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

    - query::region (str)
        The region of the player.

    """
    client = GetRiotClientByUserRegion(region, src_route=SRC_ROUTE, router=router)
    path_endpoint: str = AccountV1_Endpoints.ActiveShardForPlayer.format(game=game, puuid=puuid)
    return await QueryToRiotAPI(client, path_endpoint)
