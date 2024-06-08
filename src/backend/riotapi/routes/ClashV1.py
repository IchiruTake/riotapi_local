"""
See here for updates:
https://github.com/RiotGames/developer-relations/issues/928

"""

from time import perf_counter
from typing import Annotated

from cachetools.func import ttl_cache
from fastapi import Query
from fastapi.routing import APIRouter
from fastapi.responses import Response

from src.backend.riotapi.routes._query import QueryToRiotAPI
from src.static.static import BASE_TTL_ENTRY, BASE_TTL_DURATION, CREDENTIALS, REGION_ANNOTATED_PATTERN
from src.backend.riotapi.routes._endpoints import ClashV1_Endpoints
from src.backend.riotapi.models.ClashV1 import PlayerDto, TeamDto, TournamentDto

# ==================================================================================================
router = APIRouter()
SRC_ROUTE: str = str(__name__).split('.')[-1]
_CREDENTIALS = [CREDENTIALS.LOL, CREDENTIALS.FULL]


# ==================================================================================================
@ttl_cache(maxsize=BASE_TTL_ENTRY, ttl=BASE_TTL_DURATION, timer=perf_counter, typed=True)
@router.get("/by-summoner/{summonerId}", response_model=PlayerDto, tags=[SRC_ROUTE])
async def GetPlayerBySummonerId(
        response: Response,
        summonerId: str,
        region: Annotated[str | None, Query(pattern=REGION_ANNOTATED_PATTERN)] = None,
) -> PlayerDto:
    f"""
    {ClashV1_Endpoints.GetBySummonerId}
    Get players by summoner ID.

    Arguments:
    ---------

    - path::summonerId (str)
        The player's summoner ID.

    - query::region (str)
        The region where the player is located.
    
    """
    endpoint: str = ClashV1_Endpoints.GetBySummonerId.format(summonerId=summonerId)
    return await QueryToRiotAPI(host=region, credentials=_CREDENTIALS, endpoint=endpoint, router=router,
                                method="GET", params=None, headers=None, cookies=None, usr_response=response)


@ttl_cache(maxsize=BASE_TTL_ENTRY, ttl=BASE_TTL_DURATION, timer=perf_counter, typed=True)
@router.get("/teams/{teamId}", response_model=TeamDto, tags=[SRC_ROUTE])
async def GetTeamById(
        response: Response,
        teamId: str,
        region: Annotated[str | None, Query(pattern=REGION_ANNOTATED_PATTERN)] = None,
) -> TeamDto:
    f"""
    {ClashV1_Endpoints.GetByTeamId}
    Get team by ID.

    Arguments:
    ---------

    - path::teamId (str)
        The team's ID.

    - query::region (str)
        The region where the player is located.

    """
    endpoint: str = ClashV1_Endpoints.GetByTeamId.format(teamId=teamId)
    return await QueryToRiotAPI(host=region, credentials=_CREDENTIALS, endpoint=endpoint, router=router,
                                method="GET", params=None, headers=None, cookies=None, usr_response=response)


@ttl_cache(maxsize=BASE_TTL_ENTRY, ttl=BASE_TTL_DURATION, timer=perf_counter, typed=True)
@router.get("/", response_model=TournamentDto, tags=[SRC_ROUTE])
async def GetTournaments(
        response: Response,
        region: Annotated[str | None, Query(pattern=REGION_ANNOTATED_PATTERN)] = None,
) -> TournamentDto:
    f"""
    {ClashV1_Endpoints.GetTournaments}
    Get all active or upcoming tournaments.

    Arguments:
    ---------

    - query::region (str)
        The region where the player is located.

    """
    endpoint: str = ClashV1_Endpoints.GetTournaments
    return await QueryToRiotAPI(host=region, credentials=_CREDENTIALS, endpoint=endpoint, router=router,
                                method="GET", params=None, headers=None, cookies=None, usr_response=response)


@ttl_cache(maxsize=BASE_TTL_ENTRY, ttl=BASE_TTL_DURATION, timer=perf_counter, typed=True)
@router.get("/by-team/{teamId}", response_model=TournamentDto, tags=[SRC_ROUTE])
async def GetTournamentByTeamId(
        response: Response,
        teamId: str,
        region: Annotated[str | None, Query(pattern=REGION_ANNOTATED_PATTERN)] = None,
) -> TournamentDto:
    f"""
    {ClashV1_Endpoints.GetTournamentByTeamId}
    Get tournament by teamId

    Arguments:
    ---------
    
    - path::teamId (str)
        The team's ID.
    
    - query::region (str)
        The region where the player is located.

    """
    endpoint: str = ClashV1_Endpoints.GetTournamentByTeamId.format(teamId=teamId)
    return await QueryToRiotAPI(host=region, credentials=_CREDENTIALS, endpoint=endpoint, router=router,
                                method="GET", params=None, headers=None, cookies=None, usr_response=response)


@ttl_cache(maxsize=BASE_TTL_ENTRY, ttl=BASE_TTL_DURATION, timer=perf_counter, typed=True)
@router.get("/{tournamentId}", response_model=TournamentDto, tags=[SRC_ROUTE])
async def GetTournamentById(
        response: Response,
        tournamentId: str,
        region: Annotated[str | None, Query(pattern=REGION_ANNOTATED_PATTERN)] = None,
) -> TournamentDto:
    f"""
    {ClashV1_Endpoints.GetTournamentByTeamId}
    Get tournament by Id

    Arguments:
    ---------

    - path::tournamentId (str)
        The tournament's ID.

    - query::region (str)
        The region where the player is located.

    """
    endpoint: str = ClashV1_Endpoints.GetTournamentByTournamentId.format(tournamentId=tournamentId)
    return await QueryToRiotAPI(host=region, credentials=_CREDENTIALS, endpoint=endpoint, router=router,
                                method="GET", params=None, headers=None, cookies=None, usr_response=response)