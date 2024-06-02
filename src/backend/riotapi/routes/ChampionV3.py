from time import perf_counter
from typing import Annotated

from cachetools.func import ttl_cache
from fastapi import Query
from fastapi.routing import APIRouter

from src.backend.riotapi.routes._region import GetRiotClientByUserRegion, QueryToRiotAPI, \
    REGION_ANNOTATED_PATTERN
from src.utils.static import BASE_TTL_ENTRY, BASE_TTL_DURATION
from src.backend.riotapi.routes._endpoints import ChampionV3_Endpoints
from src.backend.riotapi.models.ChampionV3 import ChampionInfo

# ==================================================================================================
router = APIRouter()
SRC_ROUTE: str = str(__name__).split('.')[-1]


@ttl_cache(maxsize=BASE_TTL_ENTRY, ttl=BASE_TTL_DURATION, timer=perf_counter, typed=True)
@router.get("/", response_model=ChampionInfo, tags=[SRC_ROUTE])
async def GetChampionRotation(
        region: Annotated[str | None, Query(pattern=REGION_ANNOTATED_PATTERN)] = None
    ) -> ChampionInfo:
    f"""
    {ChampionV3_Endpoints.ChampionRotation}
    Returns champion rotations, including free-to-play and low-level free-to-play rotations (REST)

    Arguments:
    ---------

    - query::region (str)
        The region of the player.

    """
    client = GetRiotClientByUserRegion(region, src_route=SRC_ROUTE, router=router)
    path_endpoint: str = ChampionV3_Endpoints.ChampionRotation
    return await QueryToRiotAPI(client, path_endpoint)
