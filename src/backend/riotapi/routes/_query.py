import logging
from typing import Any, Annotated

from fastapi import APIRouter, HTTPException, FastAPI
from httpx import AsyncClient
from httpx import Response as HttpxResponse
from starlette.status import (HTTP_400_BAD_REQUEST, HTTP_500_INTERNAL_SERVER_ERROR, HTTP_405_METHOD_NOT_ALLOWED,
                              HTTP_429_TOO_MANY_REQUESTS)
from starlette.types import ASGIApp
from starlette.types import Response as StarletteResponse

from src.backend.riotapi.client import HttpxAsyncClient
from src.backend.riotapi.routes.default import DefaultSettings
from pydantic import Field, TypeAdapter
from src.utils.static import CredentialName


# ==================================================================================================
async def Query(host: str, credential_name: str | list[str], src_route: str, router: APIRouter | FastAPI | ASGIApp,
                endpoint: str, method: str, params: dict | None = None, headers: dict | None = None,
                cookies: dict | None = None, usr_response: StarletteResponse = None) -> object | Any:
    if isinstance(credential_name, str):
        credential_name = [credential_name]
    # Validate the StrEnum of the credential name --> Then convert it to enum
    if not all([cred in CredentialName for cred in credential_name]):
        logging.error(f"Invalid credential name: {credential_name}")
        raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail="Invalid credential name")
    else:
        credential_name = [CredentialName(cred) for cred in credential_name]
        credential_name.sort(key=lambda x: x.GetPriority())

    errors: list[dict] = []
    for cred in credential_name:
        client: AsyncClient = GetRiotClientByUserRegion(host, cred, src_route, router)
        response: HttpxResponse = await QueryToRiotAPI(client, endpoint, params=params, headers=headers,
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
            logging.warning(f"Rate limit exceeded --> Switching to another credential")
            continue
        elif status_code == HTTP_405_METHOD_NOT_ALLOWED:
            logging.warning(f"Method not allowed")
            continue

    if errors:
        # Choose the error preferred to 400 and 500
        errors.sort(key=lambda x: (divmod(x['status_code'], 100)[1], x['status_code']))
        for idx, err in enumerate(errors[::-1]):
            detail = f"Error on querying on using this host {err['credential']} : {err['text']} "
            e = HTTPException(status_code=err['status_code'], detail=detail, headers=err['headers'])
            logging.error(e)
            if idx == len(errors) - 1:
                err = errors[0]
                raise HTTPException(status_code=err['status_code'], detail=f"Error on querying: {err}",
                                    headers=err['headers'])

    return None

def GetRiotClientByUserRegion(host: str, credential_name: str, src_route: str, router: APIRouter | FastAPI,
                              bypass_region_route: bool = False) -> AsyncClient:
    if not hasattr(router, 'default'):
        raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail="Invalid router configuration")

    assert isinstance(router.default, DefaultSettings)
    auth: dict = router.default.GetAuthOfKeyName(credential_name)
    timeout: dict = router.default.timeout
    return HttpxAsyncClient.GetRiotClient(region=host, credential_name=credential_name, auth=auth, timeout=timeout)


async def QueryToRiotAPI(client: AsyncClient, endpoint: str, method: str = "GET", params: dict | None = None,
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
