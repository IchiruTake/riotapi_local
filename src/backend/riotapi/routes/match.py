import logging
from time import perf_counter
from src.backend.riotapi.client.httpx_riotclient import get_riotclient
from fastapi.routing import APIRouter
from fastapi.exceptions import HTTPException
from requests import Response
from pydantic import BaseModel, Field
from cachetools.func import ttl_cache


def riotapi_region_routing(user_region: str) -> str:
    # For user account searching, any region is valid
    mapping = {
        "BR1": "AMERICAS",
        "EUN1": "EUROPE",
        "EUW1": "EUROPE",
        "JP1": "ASIA",
        "KR": "ASIA",
        "LA1": "AMERICAS",
        "LA2": "AMERICAS",
        "NA1": "AMERICAS",
        "OC1": "SEA",
        "PH2": "SEA",
        "RU": "EUROPE",
        "SG2": "SEA",
        "TH2": "SEA",
        "TR1": "EUROPE",
        "TW2": "SEA",
        "VN2": "SEA"
    }
    if user_region not in mapping:
        logging.error(f"Invalid region: {user_region}")
        raise ValueError(f"Invalid region: {user_region}")
    return mapping[user_region]

# ==================================================================================================

router = APIRouter()


@ttl_cache(maxsize=128, ttl=60, timer=perf_counter, typed=True)
@router.get("/{region}/{puuid}", response_model=list[str])
async def get_matches(region: str, puuid: str, start: int = 0, count: int = 0) -> list[str]:
    """
    Get the Riot account information of a player by their username and tagline.

    Arguments:
    ---------

    - username (str)
        The username of the player.

    - tagLine (str)
        The tagline of the player.

    """
    USERCFG = router.default_user_cfg
    try:
        region: str = riotapi_region_routing(USERCFG.REGION)
    except ValueError:
        return HTTPException(status_code=400, detail="Invalid region")
    client = get_riotclient(region=region, auth=USERCFG.AUTH, timeout=USERCFG.TIMEOUT)
    ENDPOINT: str = '/riot/account/v1/accounts/by-riot-id/{gameName}/{tagLine}'
    PATH_ENDPOINT = ENDPOINT.format(gameName=username, tagLine=tagLine)
    response: Response = await client.get(PATH_ENDPOINT)
    response.raise_for_status()
    return response.json()