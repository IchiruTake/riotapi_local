import httpx
import logging
from requests import Request, Response
from pydantic import BaseModel, Field

def log_request(request: Request) -> None:
    msg: str = f"""
        Request to {request.url} by method {request.method}
        - Headers: {request.headers}
        - Cookies: {request.cookies}
        - Data: {request.data}
        - Params: {request.params}
        - JSON: {request.json}
        - Auth: {request.auth}
    """
    logging.info(msg)

def log_response(response: Response) -> None:
    msg: str = f"""
        Response from {response.request.method} {response.url} with status code {response.status_code}
        - Elapsed: {response.elapsed}
        - Headers: {response.headers}
        - Content: {response.content}
        - History: {response.history}
    """
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

async def get_riotclient(url: str, auth: dict | None, timeout: dict | None) -> httpx.AsyncClient:
    # Configure the authentication approach with headers/params
    headers: dict = {
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Charset": "application/x-www-form-urlencoded; charset=UTF-8",
        "Origin": "https://developer.riotgames.com"
    }
    params: dict | None = None
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
        logging.warning('No authentication approach is provided, the client will be created without any authentication.')

    # Configure the timeout
    tout: httpx.Timeout | None = None
    if timeout is not None:
        tout_model: HttpTimeout = HttpTimeout(**timeout)
        tout = httpx.Timeout(timeout=tout_model.ALL, connect=tout_model.CONNECT, read=tout_model.READ,
                             write=tout_model.WRITE, pool=tout_model.POOL)

    # No proxy/proxies/mounts are supported here -> Declare for informative
    with httpx.AsyncClient(base_url=url, verify=True, http1=True, http2=True, follow_redirects=False, params=params,
                           proxy=None, proxies=None, mounts=None, headers=headers, timeout=tout,
                           default_encoding='utf-8') as client:
        # Configure the client-hooks
        client.event_hooks['request'] = [log_request]
        client.event_hooks['response'] = [log_response]
        yield client
