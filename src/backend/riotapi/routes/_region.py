import logging
from typing import Annotated, Any
from httpx import AsyncClient
from fastapi import APIRouter, HTTPException
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_500_INTERNAL_SERVER_ERROR
from requests import Response
from src.backend.riotapi.client.httpx_riotclient import get_riotclient


_RegionRoute: dict[str, dict[str, str]] = {
    "AccountV1": {"BR1": "AMERICAS", "EUN1": "EUROPE", "EUW1": "EUROPE", "JP1": "ASIA", "KR": "ASIA",
                  "LA1": "AMERICAS", "LA2": "AMERICAS", "NA1": "AMERICAS", "OC1": "ASIA", "PH2": "ASIA",
                  "RU": "EUROPE", "SG2": "ASIA", "TH2": "ASIA", "TR1": "EUROPE", "TW2": "ASIA", "VN2": "ASIA"},
    "MatchV5": {"BR1": "AMERICAS", "EUN1": "EUROPE", "EUW1": "EUROPE", "JP1": "ASIA", "KR": "ASIA",
                "LA1": "AMERICAS", "LA2": "AMERICAS", "NA1": "AMERICAS", "OC1": "SEA", "PH2": "SEA",
                "RU": "EUROPE", "SG2": "SEA", "TH2": "SEA", "TR1": "EUROPE", "TW2": "SEA", "VN2": "SEA"}
}
REGION_ANNOTATED_PATTERN: str = "|".join(list(_RegionRoute["AccountV1"].keys()))


def RegionRoute(user_region: str, src_route: str) -> str:
    if src_route not in _RegionRoute:
        logging.error(f"Invalid route: {src_route}")
        raise ValueError(f"Invalid route: {src_route}")
    if user_region not in _RegionRoute[src_route]:
        logging.error(f"Invalid region: {user_region}")
        raise ValueError(f"Invalid region: {user_region}")
    return _RegionRoute[src_route][user_region]


def GetRiotClientByUserRegionToContinent(region: str, src_route: str, router: APIRouter,
                                         bypass_region_route: bool = False) -> AsyncClient:
    try:
        USERCFG = router.default_user_cfg
        if not bypass_region_route:
            region: str = RegionRoute(region or USERCFG.REGION, src_route=src_route)
    except AttributeError as e:
        raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Invalid router configuration by {e}")
    except ValueError as e:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=f"Invalid region by {e}")
    else:
        return get_riotclient(region=region, auth=USERCFG.AUTH, timeout=USERCFG.TIMEOUT)


async def QueryToRiotAPI(client: AsyncClient, endpoint: str, params: dict | None = None,
                         headers: dict | None = None, cookies: dict | None = None) -> object | Any:
    response: Response = await client.get(endpoint, params=params, headers=headers, cookies=cookies)
    response.raise_for_status()
    return response.json()
