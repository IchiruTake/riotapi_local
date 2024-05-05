import logging

from src.backend.riotapi.client.httpx_riotclient import get_riotclient
from fastapi.routing import APIRouter
from requests import Response
from pydantic import BaseModel, Field

def riotapi_region_routing(user_region: str) -> str:
    # For user account searching, any region is valid
    # mapping = {
    #     "BR1": "AMERICAS",
    #     "EUN1": "EUROPE",
    #     "EUW1": "EUROPE",
    #     "JP1": "ASIA",
    #     "KR": "ASIA",
    #     "LA1": "AMERICAS",
    #     "LA2": "AMERICAS",
    #     "NA1": "AMERICAS",
    #     "OC1": "SEA",
    #     "PH2": "SEA",
    #     "RU": "EUROPE",
    #     "SG2": "SEA",
    #     "TH2": "SEA",
    #     "TR1": "EUROPE",
    #     "TW2": "SEA",
    #     "VN2": "SEA"
    # }
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
    return mapping[user_region]

# ==================================================================================================
router = APIRouter()
class RiotAccount(BaseModel):
    puuid: str = Field(..., title="PUUID", description="The PUUID of the player you want to track")
    gameName: str = Field(..., title="Player Name", description="The player's name of the player you want to track")
    tagLine: str = Field(..., title="Tagline", description="The tagline of the player you want to track")

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
    # region: str = request.headers.get("REGION", USERCFG.REGION)
    client = get_riotclient(region=riotapi_region_routing(USERCFG.REGION), auth=USERCFG.AUTH, timeout=USERCFG.TIMEOUT)
    ENDPOINT: str = '/riot/account/v1/accounts/by-riot-id/{gameName}/{tagLine}'
    PATH_ENDPOINT = ENDPOINT.format(gameName=username, tagLine=tagLine)
    response: Response = await client.get(PATH_ENDPOINT)
    response.raise_for_status()
    return response.json()
