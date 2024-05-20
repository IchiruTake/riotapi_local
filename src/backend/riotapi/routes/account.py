import logging
from time import perf_counter

from cachetools.func import ttl_cache
from fastapi.exceptions import HTTPException
from fastapi.routing import APIRouter
from pydantic import BaseModel, Field
from requests import Response

from src.backend.riotapi.client.httpx_riotclient import get_riotclient


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
        "OC1": "ASIA",
        "PH2": "ASIA",
        "RU": "EUROPE",
        "SG2": "ASIA",
        "TH2": "ASIA",
        "TR1": "EUROPE",
        "TW2": "ASIA",
        "VN2": "ASIA"
    }
    if user_region not in mapping:
        logging.error(f"Invalid region: {user_region}")
        raise ValueError(f"Invalid region: {user_region}")
    return mapping[user_region]


# ==================================================================================================


class RiotAccount(BaseModel):
    puuid: str = Field(..., title="PUUID", description="The PUUID of the player you want to track")
    gameName: str = Field(..., title="Player Name", description="The player's name of the player you want to track")
    tagLine: str = Field(..., title="Tagline", description="The tagline of the player you want to track")


router = APIRouter()


@ttl_cache(maxsize=16, ttl=300, timer=perf_counter, typed=True)
@router.get("/{username}/{tagLine}", response_model=RiotAccount)
async def get_riot_account(username: str, tagLine: str):
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
