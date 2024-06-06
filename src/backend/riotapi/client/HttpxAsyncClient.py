import ssl
import logging
from datetime import datetime
from pprint import pformat
import httpx
from httpx import Request, Response
from pydantic import BaseModel, Field

from src.log.timezone import GetProgramTimezone
from src.backend.riotapi.client import BaseClient


# ==================================================================================================
_HTTP1: bool = True
_HTTP2: bool = True
_VERIFY: bool | ssl.SSLContext = (httpx.create_ssl_context(cert=None, trust_env=True, verify=False, http2=_HTTP2) or
                                  ssl.create_default_context())
_PROXY: str | None = None
_PROXIES: dict[str, str] | None = None
_MOUNTS: dict[str, httpx.AsyncClient] | None = None
_FOLLOW_REDIRECTS: bool = False
_DEFAULT_ENCODING: str = 'utf-8'

# ==================================================================================================
async def _HttpxLogRequest(request: Request) -> None:
    request.headers['X-Request-Timestamp'] = datetime.now(tz=GetProgramTimezone()).isoformat()
    msg: str = f"""
Request to {request.url} by method {request.method}
- Headers: {pformat(request.headers)}"""
    logging.info(msg)

async def _HttpxLogResponse(response: Response) -> None:
    await response.aread()
    # Calculate the duration of the request
    current_datetime: datetime = datetime.now(tz=GetProgramTimezone())
    request_timestamp: str = response.request.headers['X-Request-Timestamp']
    request_datetime: datetime = datetime.fromisoformat(request_timestamp)
    request_duration: int = (current_datetime - request_datetime).microseconds // 1000
    response.headers['X-Response-Timestamp'] = current_datetime.isoformat()
    response.headers['X-Request-Timestamp'] = request_timestamp
    response.headers['X-Response-DurationInMilliseconds'] = str(request_duration)

    msg: str = f"""
Response from {response.request.method} {response.url} with status code {response.status_code}
- Elapsed: {response.elapsed}
- Text: {response.text}
- Headers: {pformat(response.headers)}"""
    response.raise_for_status()
    try:
        content: str = f"\n\t- Content: {pformat(response.json())}"
        if response.status_code >= 400:
            logging.warning(msg)
            logging.warning(content)
        else:
            logging.info(msg)
            logging.info(content)
    except (UnicodeError, UnicodeDecodeError) as e:
        pass


def _RegionHostToURLHost(region: str) -> str:
    return f"https://{region.lower()}.api.riotgames.com"


class HttpTimeout(BaseModel):
    ALL: int | float | None = Field(default=30, description='The timeout for all operations.', ge=0)
    CONNECT: int | float | None = Field(default=15, description='The timeout for connecting to the server.', ge=0)
    READ: int | float | None = Field(default=15, description='The timeout for reading the response from the server.',
                                     ge=0)
    WRITE: int | float | None = Field(default=15, description='The timeout for writing the request to the server.')
    POOL: int | float | None = Field(default=15, description='The timeout for acquiring a connection from the pool.')


class ClientSettings(BaseModel):
    HEADERS: dict = Field(default_factory=dict, title="Headers", description="The headers for the HTTP(S) request")
    PARAMS: dict = Field(default_factory=dict, title="Params", description="The params for the HTTP request")
    TIMEOUT: HttpTimeout = Field(title="Timeout", description="The timeout for the HTTP request")


@BaseClient.WrapCleanUpPool
async def CleanUpPool() -> None:
    cleanup_list = []
    for (region, credential_name), client in BaseClient.Iterate():
        if client.is_closed:
            cleanup_list.append((region, credential_name))
            continue
        if not hasattr(client, 'num_on_requests'):
            raise AttributeError(f"Client {client} does not have the attribute 'num_on_requests' (an indicator"
                                 f"to keep track how many requests are waiting to be processed).")
        if client.num_on_requests == 0:
            logging.info(f"Closed the {region.upper()} Riot {credential_name.upper()} client.")
            cleanup_list.append((region, credential_name))
            if isinstance(client, httpx.Client):
                client.close()
            elif isinstance(client, httpx.AsyncClient):
                await client.aclose()
        else:
            logging.warning(f"Client {client} has {client.num_on_requests} requests waiting to be processed.")

    # Remove un-needed clients
    for region, credential_name in cleanup_list:
        BaseClient.RemoveFromPool(region, credential_name)
    return None


def _SetHeadersParamsTimeout(auth: dict | None, timeout: dict | None) -> ClientSettings:
    headers: dict = {
        # RiotAPI - Default Headers
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Charset": "application/x-www-form-urlencoded; charset=UTF-8",
        "Origin": "https://developer.riotgames.com",
        # Custom Headers
        "Accept-Encoding": "gzip, deflate, br, zstd, identity, *;q=0.1",
    }
    params: dict = {}
    if auth is not None:
        try:
            KEY: str = auth['APIKEY']  # Must be provided
            approach: str = auth.get('PREFER_APPROACH', 'HEADER')
            match approach:
                case 'HEADER':
                    headers[auth['HEADER_NAME']] = KEY
                case 'PARAM':
                    params[auth['PARAM_NAME']] = KEY
                case _:
                    raise ValueError(f'Unknown authentication approach: {approach}')

        except KeyError as e:
            logging.error(f'Failed to configure the authentication which should contain these key entries: APIKEY, '
                          f'PREFER_APPROACH, either HEADER_NAME or PARAM_NAME. Error: {e}')
            raise e
    else:
        logging.warning('No authentication approach is provided, the client will be created without '
                        'any authentication.')
    return ClientSettings(HEADERS=headers, PARAMS=params, TIMEOUT=HttpTimeout(**timeout))


@BaseClient.WrapGetRiotClient
def GetRiotClient(region: str, credential_name: str, auth: dict | None, timeout: dict | None) -> httpx.AsyncClient:
    riotapi_client_settings = _SetHeadersParamsTimeout(auth, timeout)
    timeout = riotapi_client_settings.TIMEOUT
    riotapi_timeout = httpx.Timeout(timeout=timeout.ALL, connect=timeout.CONNECT, read=timeout.READ,
                                    write=timeout.WRITE, pool=timeout.POOL)

    # No proxy/proxies/mounts are supported here -> Declare for informative
    client = httpx.AsyncClient(base_url=_RegionHostToURLHost(region), verify=_VERIFY, http1=_HTTP1, http2=_HTTP2,
                               proxy=_PROXY, proxies=_PROXIES, mounts=_MOUNTS, follow_redirects=_FOLLOW_REDIRECTS,
                               params=riotapi_client_settings.PARAMS, headers=riotapi_client_settings.HEADERS,
                               timeout=riotapi_timeout, default_encoding=_DEFAULT_ENCODING)
    # Configure the client-hooks
    client.event_hooks['request'] = [_HttpxLogRequest]
    client.event_hooks['response'] = [_HttpxLogResponse]

    # Customize the client
    client.num_on_requests = 0
    return client
