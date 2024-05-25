import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from httpx import AsyncClient
from requests import Response
from fastapi import Response as FastAPIResponse
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_500_INTERNAL_SERVER_ERROR

from src.backend.riotapi.client.httpx_riotclient import GetRiotClient

_RegionRoute: dict[str, dict[str, str]] = {
    "AccountV1": {"BR1": "AMERICAS", "EUN1": "EUROPE", "EUW1": "EUROPE", "JP1": "ASIA", "KR": "ASIA",
                  "LA1": "AMERICAS", "LA2": "AMERICAS", "NA1": "AMERICAS", "OC1": "ASIA", "PH2": "ASIA",
                  "RU": "EUROPE", "SG2": "ASIA", "TH2": "ASIA", "TR1": "EUROPE", "TW2": "ASIA", "VN2": "ASIA"},
    "MatchV5": {"BR1": "AMERICAS", "EUN1": "EUROPE", "EUW1": "EUROPE", "JP1": "ASIA", "KR": "ASIA",
                "LA1": "AMERICAS", "LA2": "AMERICAS", "NA1": "AMERICAS", "OC1": "SEA", "PH2": "SEA",
                "RU": "EUROPE", "SG2": "SEA", "TH2": "SEA", "TR1": "EUROPE", "TW2": "SEA", "VN2": "SEA"}
}
REGION_ANNOTATED_PATTERN: str = fr'{"|".join(list(_RegionRoute["AccountV1"].keys()))}'


def GetRiotClientByUserRegionToContinent(region: str, src_route: str, router: APIRouter,
                                         bypass_region_route: bool = False) -> AsyncClient:
    if hasattr(router, 'default_user_cfg'): # pragma: no cover
        USERCFG = router.default_user_cfg
        try:
            if not bypass_region_route:
                if src_route not in _RegionRoute:
                    logging.error(f"Invalid route: {src_route}")
                    raise ValueError(f"Invalid route: {src_route}")

                usr_region: str = region or USERCFG.REGION
                if usr_region not in _RegionRoute[src_route]:
                    logging.error(f"Invalid region: {usr_region}")
                    raise ValueError(f"Invalid region: {usr_region}")
                region: str = _RegionRoute[src_route][usr_region]
        except ValueError as e:
            raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=f"Invalid region or source routing by {e}")

        return GetRiotClient(region=region, auth=USERCFG.AUTH, timeout=USERCFG.TIMEOUT)

    raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail="Invalid router configuration")


async def QueryToRiotAPI(client: AsyncClient, endpoint: str, params: dict | None = None,
                         headers: dict | None = None, cookies: dict | None = None,
                         usr_response: FastAPIResponse = None) -> object | Any:
    response: Response = await client.get(endpoint, params=params, headers=headers, cookies=cookies)
    response.raise_for_status()
    if usr_response is not None:
        try:
            usr_response.status_code = response.status_code
            usr_response.headers.update(response.headers)
            usr_response.charset = response.encoding
            media_type: str | None = response.headers.get('Content-Type', None)
            if not media_type:
                media_type = media_type.split(';')[0]
            usr_response.media_type = media_type
        except Exception as e:
            logging.warning(f"Error on updating the user's response: {e}")

    return response.json()
