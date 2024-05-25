import ssl
import logging
import time
from datetime import datetime
from pprint import pformat

import httpx
from httpx import Request, Response
from pydantic import BaseModel, Field

from src.log.timezone import GetProgramTimezone
from src.utils.utils import GetDurationOfPerfCounterInMs


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
async def _httpx_log_request(request: Request) -> None:
    request.headers['X-Request-Timestamp'] = datetime.now(tz=GetProgramTimezone()).isoformat()
    msg: str = f"""
Request to {request.url} by method {request.method}
- Headers: {pformat(request.headers)}"""
    logging.info(msg)


async def _httpx_log_response(response: Response) -> None:
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
    - Headers: {pformat(response.headers)}"""
    if response.status_code >= 400:
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


class HttpTimeout(BaseModel):
    ALL: int | float | None = Field(default=15, description='The timeout for all operations.', ge=0)
    CONNECT: int | float | None = Field(default=30, description='The timeout for connecting to the server.', ge=0)
    READ: int | float | None = Field(default=30, description='The timeout for reading the response from the server.',
                                     ge=0)
    WRITE: int | float | None = Field(default=30, description='The timeout for writing the request to the server.')
    POOL: int | float | None = Field(default=30, description='The timeout for acquiring a connection from the pool.')


_RIOT_CLIENTPOOL: dict[str, httpx.AsyncClient] = {}


def _RegionToHost(region: str) -> str:
    return f"https://{region.lower()}.api.riotgames.com"


# ==================================================================================================
class RiotClientWrapper(BaseModel):
    HEADERS: dict = Field(default_factory=dict, title="Headers", description="The headers for the HTTP(S) request")
    PARAMS: dict = Field(default_factory=dict, title="Params", description="The params for the HTTP request")
    TIMEOUT: HttpTimeout = Field(title="Timeout", description="The timeout for the HTTP request")


def _SetHeadersParamsTimeout(auth: dict | None, timeout: dict | None) -> RiotClientWrapper:
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
            if approach == 'HEADER':
                headers[auth['HEADER_NAME']] = KEY
            elif approach == 'PARAM':
                params = {auth['PARAM_NAME']: KEY}
            else:
                raise ValueError(f'Unknown authentication approach: {approach}')
        except KeyError as e:
            logging.error(f'Failed to configure the authentication which should contain these key entries: APIKEY, '
                          f'PREFER_APPROACH, either HEADER_NAME or PARAM_NAME. Error: {e}')
            raise e
    else:
        logging.warning('No authentication approach is provided, the client will be created without '
                        'any authentication.')
    return RiotClientWrapper(HEADERS=headers, PARAMS=params, TIMEOUT=HttpTimeout(**timeout))


def GetRiotClient(region: str, auth: dict | None, timeout: dict | None) -> httpx.AsyncClient:
    # Configure the authentication approach with headers/params
    if region in _RIOT_CLIENTPOOL:
        logging.info(f"Found an existing Riot client for region: {region}")
        return _RIOT_CLIENTPOOL[region]

    logging.info(f"Creating a new Riot client for region: {region}")
    t = time.perf_counter()
    riot_wrapper: RiotClientWrapper = _SetHeadersParamsTimeout(auth, timeout)

    # No proxy/proxies/mounts are supported here -> Declare for informative
    timeout = riot_wrapper.TIMEOUT
    tout = httpx.Timeout(timeout=timeout.ALL, connect=timeout.CONNECT, read=timeout.READ,
                         write=timeout.WRITE, pool=timeout.POOL)
    client = httpx.AsyncClient(base_url=_RegionToHost(region),
                               verify=_VERIFY, http1=_HTTP1, http2=_HTTP2,
                               proxy=_PROXY, proxies=_PROXIES, mounts=_MOUNTS, follow_redirects=_FOLLOW_REDIRECTS,
                               params=riot_wrapper.PARAMS, headers=riot_wrapper.HEADERS, timeout=tout,
                               default_encoding=_DEFAULT_ENCODING)
    # Configure the client-hooks
    client.event_hooks['request'] = [_httpx_log_request]
    client.event_hooks['response'] = [_httpx_log_response]
    _RIOT_CLIENTPOOL[region] = client
    logging.debug(f"Created a new Riot client for region: {region} in {GetDurationOfPerfCounterInMs(t):.2f} ms.")
    return client


async def CleanupRiotClient() -> None:
    for region, client in _RIOT_CLIENTPOOL.items():
        await client.aclose()
        logging.info(f"Closed the {region.upper()} Riot client.")

    _RIOT_CLIENTPOOL.clear()
    logging.info("Cleared the Riot client pool.")
