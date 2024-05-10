import logging
from datetime import datetime
import httpx
from pydantic import BaseModel, Field
from httpx import Request, Response
from src.log.timezone import GetProgramTimezone


async def log_request(request: Request) -> None:
    request.headers['X-Request-Timestamp'] = datetime.now(tz=GetProgramTimezone()).isoformat()
    msg: str = f"""
Request to {request.url} by method {request.method}
- Headers: {request.headers}"""
    logging.info(msg)


async def log_response(response: Response) -> None:
    await response.aread()
    msg: str = f"""
Response from {response.request.method} {response.url} with status code {response.status_code}
    - Elapsed: {response.elapsed}
    - Text: {response.text}
    - JSON: {response.json()}
    - Headers: {response.headers}
    - Content: {response.content}
    - History: {response.history}"""
    if response.status_code >= 400:
        response.raise_for_status()
        logging.warning(msg)
    else:
        logging.info(msg)


class HttpTimeout(BaseModel):
    ALL: int | float | None = Field(default=15, description='The timeout for all operations.', ge=0)
    CONNECT: int | float | None = Field(default=30, description='The timeout for connecting to the server.', ge=0)
    READ: int | float | None = Field(default=30, description='The timeout for reading the response from the server.',
                                     ge=0)
    WRITE: int | float | None = Field(default=30, description='The timeout for writing the request to the server.')
    POOL: int | float | None = Field(default=30, description='The timeout for acquiring a connection from the pool.')


_RIOT_CLIENTPOOL: dict[str, httpx.AsyncClient] = {}

def region_to_host(region: str) -> str:
    return f"https://{region.lower()}.api.riotgames.com"

async def cleanup_riotclient() -> None:
    for region, client in _RIOT_CLIENTPOOL.items():
        await client.aclose()
        logging.info(f"Closed the Riot client for region: {region}")

    _RIOT_CLIENTPOOL.clear()
    logging.info("Cleared the Riot client pool.")

class RiotClientWrapper(BaseModel):
    HEADERS: dict = Field(default_factory=dict, title="Headers", description="The headers for the HTTP(S) request")
    PARAMS: dict = Field(default_factory=dict, title="Params", description="The params for the HTTP request")
    TIMEOUT: HttpTimeout = Field(title="Timeout", description="The timeout for the HTTP request")

def _set_headers_params_timeout(auth: dict | None, timeout: dict | None) -> RiotClientWrapper:
    headers: dict = {
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Charset": "application/x-www-form-urlencoded; charset=UTF-8",
        "Origin": "https://developer.riotgames.com"
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
        logging.warning(
            'No authentication approach is provided, the client will be created without any authentication.')
    return RiotClientWrapper(HEADERS=headers, PARAMS=params, TIMEOUT=HttpTimeout(**timeout))


def get_riotclient(region: str, auth: dict | None, timeout: dict | None) -> httpx.AsyncClient:
    # Configure the authentication approach with headers/params
    if region in _RIOT_CLIENTPOOL:
        logging.info(f"Found an existing Riot client for region: {region}")
        return _RIOT_CLIENTPOOL[region]

    logging.info(f"Creating a new Riot client for region: {region}")
    riot_wrapper: RiotClientWrapper = _set_headers_params_timeout(auth, timeout)

    # No proxy/proxies/mounts are supported here -> Declare for informative
    timeout = riot_wrapper.TIMEOUT
    tout = httpx.Timeout(timeout=timeout.ALL, connect=timeout.CONNECT, read=timeout.READ,
                         write=timeout.WRITE, pool=timeout.POOL)
    client = httpx.AsyncClient(base_url=region_to_host(region), verify=True, http1=True, http2=True, proxy=None,
                               proxies=None, mounts=None, follow_redirects=False, params=riot_wrapper.PARAMS,
                               headers=riot_wrapper.HEADERS, timeout=tout, default_encoding='utf-8')
    # Configure the client-hooks
    client.event_hooks['request'] = [log_request]
    client.event_hooks['response'] = [log_response]
    _RIOT_CLIENTPOOL[region] = client
    return client
