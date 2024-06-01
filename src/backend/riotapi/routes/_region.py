import logging
from typing import Any

from fastapi import APIRouter, HTTPException, FastAPI
from httpx import AsyncClient, Response
from fastapi import Response as FastAPIResponse
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_500_INTERNAL_SERVER_ERROR

from src.backend.riotapi.client import HttpxAsyncClient


# ==================================================================================================
_Continents: dict[str, list[str]] = {
    "C1": ["AMERICAS", "EUROPE", "ASIA", "ESPORTS"],
    "C2": ["AMERICAS", "EUROPE", "ASIA", "SEA"]
}
_RegionRoute: dict[str, dict[str, str]] = {
    "AccountV1": {"BR1": "AMERICAS", "EUN1": "EUROPE", "EUW1": "EUROPE", "JP1": "ASIA", "KR": "ASIA",
                  "LA1": "AMERICAS", "LA2": "AMERICAS", "NA1": "AMERICAS", "OC1": "ASIA", "PH2": "ASIA",
                  "RU": "EUROPE", "SG2": "ASIA", "TH2": "ASIA", "TR1": "EUROPE", "TW2": "ASIA", "VN2": "ASIA"},
    "MatchV5": {"BR1": "AMERICAS", "EUN1": "EUROPE", "EUW1": "EUROPE", "JP1": "ASIA", "KR": "ASIA",
                "LA1": "AMERICAS", "LA2": "AMERICAS", "NA1": "AMERICAS", "OC1": "SEA", "PH2": "SEA",
                "RU": "EUROPE", "SG2": "SEA", "TH2": "SEA", "TR1": "EUROPE", "TW2": "SEA", "VN2": "SEA"}
}
_RegionList: list[str] = list(_RegionRoute["AccountV1"].keys()) + list(_RegionRoute["MatchV5"].keys())
_RegionList = list(set(_RegionList))
_ContinentList: list[str] = list(_RegionRoute["AccountV1"].values()) + list(_RegionRoute["MatchV5"].values())
_ContinentList = list(set(_ContinentList))
REGION_ANNOTATED_PATTERN: str = fr'{"|".join(_RegionList)}'
CONTINENT_ANNOTATED_PATTERN: str = fr'{"|".join(_ContinentList)}'


def GetRiotClientByUserRegion(region: str, credential_name: str, src_route: str, router: APIRouter | FastAPI,
                              bypass_region_route: bool = False) -> AsyncClient:
    if hasattr(router, 'default_user_cfg'): # pragma: no cover
        USERCFG = router.default_user_cfg
        try:
            if not bypass_region_route:
                if src_route not in _RegionRoute:
                    logging.error(f"Invalid route: {src_route}", exc_info=True)
                    raise ValueError(f"Invalid route: {src_route}")

                usr_region: str = region or USERCFG.REGION
                if usr_region not in _RegionRoute[src_route]:
                    logging.error(f"Invalid region: {usr_region}", exc_info=True)
                    raise ValueError(f"Invalid region: {usr_region}")
                region: str = _RegionRoute[src_route][usr_region]
        except ValueError as e:
            raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=f"Invalid region or source routing by {e}")

        return HttpxAsyncClient.GetRiotClient(region=region, credential_name=credential_name,
                                              auth=USERCFG.AUTH, timeout=USERCFG.TIMEOUT)

    raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail="Invalid router configuration")


async def QueryToRiotAPI(client: AsyncClient, endpoint: str, params: dict | None = None,
                         headers: dict | None = None, cookies: dict | None = None,
                         usr_response: FastAPIResponse = None) -> object | Any:
    if hasattr(client, "num_on_requests"):
        client.num_on_requests += 1
    response: Response = await client.get(endpoint, params=params, headers=headers, cookies=cookies)
    if hasattr(client, "num_on_requests"):
        client.num_on_requests -= 1
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

            # Set the response content
            usr_response.content = response.content

            # Set the response body
            usr_response.body = response.text
            usr_response.text = response.text

        except Exception as e:
            logging.warning(f"Error on updating the user's response: {e}")

    return response  # response.json()
