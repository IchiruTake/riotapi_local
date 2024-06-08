import logging
from typing import Any

from fastapi import APIRouter, HTTPException, FastAPI
from httpx import AsyncClient
from httpx import Response as HttpxResponse
from starlette.status import (HTTP_500_INTERNAL_SERVER_ERROR, HTTP_405_METHOD_NOT_ALLOWED,
                              HTTP_429_TOO_MANY_REQUESTS)
from starlette.types import ASGIApp
from starlette.responses import Response as StarletteResponse

from src.backend.riotapi.client import HttpxAsyncClient
from src.backend.riotapi.inapp import DefaultSettings
from src.static.static import (CREDENTIALS, REGION_ANNOTATED_PATTERN, MATCH_CONTINENT_ANNOTATED_PATTERN,
                               NORMAL_CONTINENT_ANNOTATED_PATTERN)
from enum import StrEnum
from src.backend.riotapi.routes.CustomAPIRouter import CustomAPIRouter


# ==================================================================================================
class _Pattern(StrEnum):
    REGION = REGION_ANNOTATED_PATTERN
    NORMAL_CONTINENT = NORMAL_CONTINENT_ANNOTATED_PATTERN
    MATCH_CONTINENT = MATCH_CONTINENT_ANNOTATED_PATTERN

def _PatchCredential(credentials: CREDENTIALS | list[CREDENTIALS], endpoint: str | None,
                     override: bool = False) -> list[CREDENTIALS]:
    """
    This function is used to patch the credential based on the endpoint and the credential name, ensuring that
    the provided :arg:`credentials` is valid and can be used to query the Riot API.

    Arguments:
    ---------

    - credentials (:enum:`CREDENTIALS` | list[:enum:`CREDENTIALS`]):
        The credential name to be used to query the Riot API.

    - endpoint (str | None):
        The endpoint to be used to query the Riot API, which can be collected via Riot API documentation, or cached
        endpoints stored in the riotapi.models module. If None, then it will not be used to filter the credential.

    - override (bool):
        If True, then it will override the provided credential to the default credential based on the endpoint.
        If False, then it will filter the credential based on the endpoint.

    Returns:
    -------

    - list[:enum:`CREDENTIALS`]:
        The filtered and sorted credential based on the endpoint and the credential name. The sorting order is based on
        the priority of the credential name. The priority can be found under the static/static.py module.

    """

    if not isinstance(credentials, list):
        credentials = list(credentials)

    # Validate the StrEnum of the credential name --> Then convert it to enum
    if not all(isinstance(cred, CREDENTIALS) for cred in credentials):
        logging.critical(f"Invalid credential name provided, expecting one or many of {CREDENTIALS}")
        raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail="Invalid credential name")

    # Add additional check to remove unnecessary credentials during query.
    # However, it is not guaranteed that the endpoint is always the first part of the path and fully
    # query-able; just a pre-check to remove accidental query.
    if endpoint is not None:
        entry_name: str = endpoint.split(r'/')[0]
        accept_paths = {
            "riot": list(CREDENTIALS.__members__.keys()),  # Fully-accepted every credential
            "lol": [CREDENTIALS.LOL, CREDENTIALS.FULL],  # Accept only LOL and FULL
            "lor": [CREDENTIALS.LOR, CREDENTIALS.FULL],  # Accept only LOR and FULL
            "tft": [CREDENTIALS.TFT, CREDENTIALS.FULL],  # Accept only TFT and FULL
            "val": [CREDENTIALS.VAL, CREDENTIALS.FULL],  # Accept only VAL and FULL
        }
        if endpoint.split(r'/')[0] in accept_paths:
            credentials = [cred for cred in credentials if cred in accept_paths[entry_name]] \
                if not override else accept_paths[entry_name]
        else:
            msg: str = "Either the endpoint is invalid, or non-registered/defined, or incorrect credential"
            logging.critical(msg)
            raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=msg)

    credentials.sort(key=lambda x: x.GetPriority(), reverse=False)
    return credentials

def _GetRiotClientByUserRegion(host: str, credential_name: str, router: CustomAPIRouter | APIRouter,
                               host_pattern: str | None = None) -> AsyncClient:
    if not isinstance(router, CustomAPIRouter):
        if not hasattr(router, 'inapp_default'):
            raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail="Invalid router configuration")

    if not isinstance(router.inapp_default, DefaultSettings):
        raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail="Invalid router configuration")

    if host is None:
        msg: str = "The :arg:`host` and :arg:`host_pattern` cannot be None at the same time"
        if host_pattern is None:
            logging.critical(msg)
            raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=msg)
        match host_pattern:
            case _Pattern.REGION:
                host = router.inapp_default.region
            case _Pattern.NORMAL_CONTINENT:
                host = router.inapp_default.continent
            case _Pattern.MATCH_CONTINENT:
                host = router.inapp_default.match_continent
            case _:
                msg: str = "Invalid host pattern provided"
                logging.critical(msg)
                raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=msg)

    auth: dict = router.inapp_default.GetAuthOfKeyName(credential_name)
    timeout: dict = router.inapp_default.timeout
    return HttpxAsyncClient.GetRiotClient(region=host, credential_name=credential_name, auth=auth, timeout=timeout)


async def _QueryToRiotAPI(client: AsyncClient, endpoint: str, method: str = "GET", params: dict | None = None,
                          headers: dict | None = None, cookies: dict | None = None,
                          usr_response: StarletteResponse = None) -> object | Any:
    if hasattr(client, "num_on_requests"):
        client.num_on_requests += 1
    match method.upper():
        case "GET":
            response: HttpxResponse = await client.get(endpoint, params=params, headers=headers, cookies=cookies)
        # case "POST":
        #     response: HttpxResponse = await client.post(endpoint, data=params, headers=headers, cookies=cookies)
        # case "PUT":
        #     response: HttpxResponse = await client.put(endpoint, data=params, headers=headers, cookies=cookies)
        # case "DELETE":
        #     response: HttpxResponse = await client.delete(endpoint, headers=headers, cookies=cookies)
        # case "PATCH":
        #     response: HttpxResponse = await client.patch(endpoint, data=params, headers=headers, cookies=cookies)
        case _:
            raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail="Invalid method sent to Riot API")
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


async def QueryToRiotAPI(host: str | None, credentials: CREDENTIALS | list[CREDENTIALS], endpoint: str,
                         router: CustomAPIRouter | APIRouter | FastAPI | ASGIApp, method: str = "GET",
                         override_credential: bool = False,
                         params: dict | None = None, headers: dict | None = None, cookies: dict | None = None,
                         usr_response: StarletteResponse = None, host_pattern: str | None = None) -> object | Any:
    credentials = _PatchCredential(credentials, path_endpoint=endpoint, override_credential=override_credential)
    errors: list[dict] = []
    for cred in credentials:
        client: AsyncClient = _GetRiotClientByUserRegion(host, cred, router, host_pattern=host_pattern)
        response: HttpxResponse = await _QueryToRiotAPI(client, endpoint, method=method, params=params, headers=headers,
                                                        cookies=cookies, usr_response=usr_response)
        status_code: int = response.status_code
        if status_code // 100 == 2:
            return response.json()
        if status_code // 100 == 1:     # DEBUG HTTP_STATUS_CODE
            continue
        if status_code // 100 != 3:     # REDIRECT HTTP_STATUS_CODE
            errors.append({'credential': cred, 'status_code': status_code, 'headers': response.headers,
                           'message': response.text or response.json()})

        # Now perform rotation or something based on HTTP status code
        if status_code == HTTP_429_TOO_MANY_REQUESTS:
            logging.warning("Rate limit exceeded --> Switching to another credential")
            continue
        elif status_code == HTTP_405_METHOD_NOT_ALLOWED:
            logging.warning("Method not allowed")
            continue

    if errors:
        # Choose the error preferred to 400 and 500
        errors.sort(key=lambda x: (divmod(x['status_code'], 100)[1], x['status_code']))
        for idx, err in enumerate(errors[::-1]):
            detail = f"Error on querying on using this host {err['credential']} : {err['text']}."
            e = HTTPException(status_code=err['status_code'], detail=detail, headers=err['headers'])
            logging.error(e)
            if idx == len(errors) - 1:
                err = errors[0]
                raise HTTPException(status_code=err['status_code'], detail=f"Error on querying: {err}",
                                    headers=err['headers'])

    return None
