import logging
import random
import string
from datetime import datetime
from functools import lru_cache
from zoneinfo import ZoneInfo
import yaml

import toml
from fastapi import FastAPI, APIRouter
from pydantic import BaseModel, Field
from starlette.middleware.sessions import SessionMiddleware
from src.backend.riotapi.client.httpx_riotclient import cleanup_riotclient
from src.backend.riotapi.middlewares.expiry_time import ExpiryTimeMiddleware
from src.backend.riotapi.middlewares.ratelimit import RateLimiterMiddleware
from src.utils.static import DAY, RIOTAPI_LOG_CFG_FILE, RIOTAPI_ENV_CFG_FILE
from contextlib import asynccontextmanager
from src.backend.riotapi.routes.account import router as account_router

# import os
# import sys
# print(os.environ["PYTHONPATH"])
# print(sys.path)

# ==================================================================================================

@lru_cache(maxsize=8, typed=True)
def _load_datetime(year: int, month: int, day: int, hour: int, minute: int, second: int, timezone: str) -> datetime:
    return datetime(year=year, month=month, day=day, hour=hour, minute=minute, second=second, tzinfo=ZoneInfo(timezone))


def load_expiry_time() -> datetime:
    with open(RIOTAPI_ENV_CFG_FILE, 'r') as riotapi_environment:
        config = toml.load(riotapi_environment)
        deadline_cfg = config['riotapi']['key']['expiry_date']
        YEAR = deadline_cfg['YEAR']
        MONTH = deadline_cfg['MONTH']
        DAY = deadline_cfg['DAY']
        HOUR = deadline_cfg['HOUR']
        MINUTE = deadline_cfg['MINUTE']
        SECOND = deadline_cfg['SECOND']
        TIMEZONE = deadline_cfg['TIMEZONE']
        return _load_datetime(YEAR, MONTH, DAY, HOUR, MINUTE, SECOND, TIMEZONE)


class RIOTAPI_USER(BaseModel):
    PUUID: str | None = Field(None, title="PUUID", description="The PUUID of the player you want to track")
    USERNAME: str = Field(..., title="Username", description="The username of the player you want to track")
    TAGLINE: str = Field(..., title="Tagline", description="The tagline of the player you want to track")
    REGION: str = Field(..., title="Region", description="The region of the player you want to track")


@asynccontextmanager
async def riotapi_lifespan(app: FastAPI):
    # On-Startup
    from src.log.log import presetDefaultLogging
    with open(RIOTAPI_LOG_CFG_FILE, 'r') as riotapi_environment:
        data = yaml.safe_load(riotapi_environment)
        presetDefaultLogging(data['LOGGER'])

    # Application Initialization
    yield

    # Clean up and release the resources
    await cleanup_riotclient()
    logging.log(logging.INFO, "Safely shutting down the application ...")

# ==================================================================================================
# FastAPI declaration and Middlewares
FASTAPI_CONFIG = {
    'DEBUG': False,
    'TITLE': 'RIOTAPI_LOCAL',
    'SUMMARY': 'RIOTAPI_LOCAL: A local-hosted Riot API (LOL) to simulate an up-to-date information during gameplay of'
               'one player you want to track information',
    'DESCRIPTION': 'RIOTAPI_LOCAL: A local-hosted Riot API (LOL) to simulate an up-to-date information during gameplay '
                   'of one player you want to track information',
    'VERSION': '0.0.1',
    'OPENAPI_URL': '/openapi.json',
    'DOCS_URL': '/docs',
    'REDOC_URL': '/redoc',
    'SWAGGER_UI_OAUTH2_REDIRECT_URL': '/docs/oauth2-redirect',
    # https://fastapi.tiangolo.com/tutorial/middleware/
    'ON_STARTUP': None,
    'ON_SHUTDOWN': None,
    'LIFESPAN': riotapi_lifespan,
    'TERMS_OF_SERVICE': None,
    'CONTACT': {
        'name': 'Ichiru Take',
        'url': 'https://github.com/IchiruTake',
        'email': 'P.Ichiru.HoangMinh@gmail.com',
    },
    'LICENSE_INFO': {
        # MIT License
        'name': 'MIT License',
        'url': 'https://opensource.org/license/mit/',
    },
    'ROOT_PATH': '',
    'ROOT_PATH_IN_SERVERS': True,
    'RESPONSES': None,
    'CALLBACKS': None,
    'WEBHOOKS': None,
    'DEPRECATED': None,
    'SEPARATE_INPUT_OUTPUT_SCHEMAS': True,
    'INCLUDE_IN_SCHEMA': True,
}

app: FastAPI = FastAPI(
    debug=FASTAPI_CONFIG.get('DEBUG', False),
    title=FASTAPI_CONFIG.get('TITLE'),
    summary=FASTAPI_CONFIG.get('SUMMARY'),
    description=FASTAPI_CONFIG.get('DESCRIPTION'),
    version=FASTAPI_CONFIG.get('VERSION'),
    openapi_url=FASTAPI_CONFIG.get('OPENAPI_URL'),
    docs_url=FASTAPI_CONFIG.get('DOCS_URL'),
    redoc_url=FASTAPI_CONFIG.get('REDOC_URL'),
    swagger_ui_oauth2_redirect_url=FASTAPI_CONFIG.get('SWAGGER_UI_OAUTH2_REDIRECT_URL'),
    # middleware=FASTAPI_CONFIG.get('MIDDLEWARE', None),
    # on_startup=FASTAPI_CONFIG.get('ON_STARTUP', None),
    # on_shutdown=FASTAPI_CONFIG.get('ON_SHUTDOWN', None),
    lifespan=FASTAPI_CONFIG.get('LIFESPAN', None),
    terms_of_service=FASTAPI_CONFIG.get('TERMS_OF_SERVICE'),
    contact=FASTAPI_CONFIG.get('CONTACT'),
    license_info=FASTAPI_CONFIG.get('LICENSE_INFO', None),
    # root_path=FASTAPI_CONFIG.get('ROOT_PATH', ''),
    # root_path_in_servers=FASTAPI_CONFIG.get('ROOT_PATH_IN_SERVERS', True),
    # responses=FASTAPI_CONFIG.get('RESPONSES', None),
    # callbacks=FASTAPI_CONFIG.get('CALLBACKS', None),
    # webhooks=FASTAPI_CONFIG.get('WEBHOOKS', None),
    # deprecated=FASTAPI_CONFIG.get('DEPRECATED', None),
    # separate_input_output_schemas=FASTAPI_CONFIG.get('SEPARATE_INPUT_OUTPUT_SCHEMAS', True),
    # include_in_schema=FASTAPI_CONFIG.get('INCLUDE_IN_SCHEMA', True),
)


# ==================================================================================================
class USER_CFG(BaseModel):
    REGION: str = Field(..., title="Region", description="The region of the player you want to track")
    TIMEOUT: dict = Field(default_factory=dict, title="Timeout", description="The timeout for the HTTP request")
    AUTH: dict = Field(default_factory=dict, title="Authorization", description="The API key for the Riot API")


SECRET_KEY = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY, max_age=DAY, https_only=False)  # 1-day session
app.add_middleware(ExpiryTimeMiddleware, deadline=load_expiry_time)
with open(RIOTAPI_ENV_CFG_FILE, 'r') as riotapi_environment:
    config = toml.load(riotapi_environment)
    cfg = config["riotapi"]["limit"]["global"]
    # Set global rate limit
    for _, value in cfg.items():
        MAX_REQUESTS: int = value["MAX_REQUESTS"]
        REQUESTS_INTERVAL: int = value["REQUESTS_INTERVAL"]
        app.add_middleware(RateLimiterMiddleware, max_requests=MAX_REQUESTS, interval_by_second=REQUESTS_INTERVAL)


# ==================================================================================================
APIROUTER_MAPPING: dict[str, APIRouter] = {
    "/account/v1": account_router
}

with open(RIOTAPI_ENV_CFG_FILE, 'r') as riotapi_environment:
    config = toml.load(riotapi_environment)
    # Set tracking users
    cfg = config["riotapi"]["user"]
    app.user = RIOTAPI_USER(**cfg)

    # Set authentication/timeout/... for shared resources
    user_cfg = {
        "REGION": config["riotapi"]["user"]["REGION"],
        "TIMEOUT": config["riotapi"]["httpx_timeout"],
        "AUTH": config["riotapi"]["key"]
    }
    global_user_cfg = USER_CFG(**user_cfg)
    for path, router in APIROUTER_MAPPING.items():
        app.include_router(router, prefix=path)
        router.default_user = app.user
        router.default_user_cfg = global_user_cfg

@app.get("/")
async def root():
    return {"message": "Hello World"}
