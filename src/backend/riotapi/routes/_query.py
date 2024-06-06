import logging
from typing import Any

from fastapi import APIRouter, HTTPException, FastAPI
from httpx import AsyncClient, Response
from fastapi import Response as FastAPIResponse
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_500_INTERNAL_SERVER_ERROR

from src.backend.riotapi.client import HttpxAsyncClient
from src.backend.riotapi.routes.default import DefaultSettings

# ==================================================================================================

def GetRiotClientByUserRegion(host: str, credential_name: str, src_route: str, router: APIRouter | FastAPI,
                              bypass_region_route: bool = False) -> AsyncClient:
    if not hasattr(router, 'default'):
        raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail="Invalid router configuration")

    assert isinstance(router.default, DefaultSettings)
    USERCFG = router.default
    auth: dict = router.default.GetAuthOfKeyName(credential_name)
    timeout: dict = router.default.timeout
    try:
        if not bypass_region_route:
            if src_route not in _RegionRoute:
                logging.error(f"Invalid route: {src_route}", exc_info=True)
                raise ValueError(f"Invalid route: {src_route}")

            usr_region: str = host or USERCFG.REGION
            if usr_region not in _RegionRoute[src_route]:
                logging.error(f"Invalid region: {usr_region}", exc_info=True)
                raise ValueError(f"Invalid region: {usr_region}")
            host: str = _RegionRoute[src_route][usr_region]
    except ValueError as e:
        msg: str = f"Invalid region or source routing by {e}"
        logging.error(msg)
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=msg)

    return HttpxAsyncClient.GetRiotClient(region=host, credential_name=credential_name, auth=auth, timeout=timeout)


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
            media_type: str | None = (response.headers.get('Content-Type', None) or
                                      response.headers.get('content-type', None))
            if not media_type:
                media_type = media_type.split(';')[0]
            usr_response.media_type = media_type

        except Exception as e:
            logging.warning(f"Error on updating the user's response: {e}")

    return response  # response.json()
