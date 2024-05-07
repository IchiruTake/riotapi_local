from time import perf_counter

from cachetools.func import ttl_cache

from src.backend.riotapi.client.httpx_riotclient import get_riotclient
from fastapi.routing import APIRouter
from requests import Response
from pydantic import BaseModel, Field
from fastapi.exceptions import HTTPException


# ==================================================================================================
class ChampionMastery(BaseModel):
    puuid: str = Field(..., title="PUUID", description="The PUUID of the player you want to track", max_length=78, frozen=True)
    championId: int = Field(..., description="Champion ID for this entry.")
    championLevel: int = Field(..., description="Champion level for specified player and champion combination.")
    championPoints: int = Field(..., description="Total number of champion points for this player and champion combination - they are used to determine championLevel.")
    lastPlayTime: int = Field(..., description="Last time this champion was played by this player - in Unix seconds time format.")
    championPointsSinceLastLevel: int = Field(..., description="Number of points earned since current level has been achieved.")
    championPointsUntilNextLevel: int = Field(..., description="Number of points needed to achieve next level. Zero if player reached maximum champion level for this champion.")
    chestGranted: bool = Field(..., description="Is chest granted for this champion or not in current season.")
    tokensEarned: int = Field(..., description="The token earned for this champion at the current championLevel. When the championLevel is advanced the tokensEarned resets to 0.")
    summonerId: str = Field(..., description="Summoner ID for this entry. (Encrypted)", frozen=True)


router = APIRouter()


@router.get("/{region}/{puuid}", response_model=list[ChampionMastery])
async def get_champion_mastery(puuid: str, region: str) -> list[ChampionMastery]:
    USERCFG = router.default_user_cfg
    USER_REGION: str = region or USERCFG.REGION
    if USER_REGION not in ('BR1', 'EUN1', 'EUW1', 'JP1', 'KR', 'LA1', 'LA2', 'NA1', 'OC1', 'PH2', 'RU',
                           'SG2', 'TH2', 'TR1', 'TW2', 'VN2'):
        raise HTTPException(status_code=400, detail="Invalid region")

    # region: str = request.headers.get("REGION", USERCFG.REGION)
    client = get_riotclient(region=region or USERCFG.REGION, auth=USERCFG.AUTH, timeout=USERCFG.TIMEOUT)
    ENDPOINT: str = '/lol/champion-mastery/v4/champion-masteries/by-puuid/{puuid}'
    PATH_ENDPOINT = ENDPOINT.format(puuid=puuid)
    response: Response = await client.get(PATH_ENDPOINT)
    response.raise_for_status()
    return response.json()


@ttl_cache(maxsize=128, ttl=120, timer=perf_counter, typed=True)
async def process_champion_mastery(puuid: str, region: str) -> list[ChampionMastery]:
    champion_mastery_list = await get_champion_mastery(puuid, region)
    for mastery in champion_mastery_list:
        mastery.lastPlayTime = mastery.lastPlayTime // 1000
    champion_mastery_list.sort(key=lambda x: x.championPoints, reverse=True)

    return champion_mastery_list
