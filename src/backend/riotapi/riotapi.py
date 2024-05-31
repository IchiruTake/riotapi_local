import asyncio
import logging
import random
import string
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from functools import lru_cache
from zoneinfo import ZoneInfo

import toml
from cachetools.func import ttl_cache
from fastapi import FastAPI, APIRouter
from pydantic import BaseModel, Field
from starlette.middleware.sessions import SessionMiddleware
from starlette.types import ASGIApp

from src.backend.riotapi.client.httpx_riotclient import CleanupRiotClient
from src.backend.riotapi.middlewares.expiry_time import ExpiryTimeMiddleware
from src.backend.riotapi.middlewares.monitor import ReworkedApitallyMiddleware
from src.backend.riotapi.middlewares.ratelimit import RateLimiterMiddleware
from src.backend.riotapi.routes.AccountV1 import router as AccountV1_router
from src.backend.riotapi.routes.LolChallengesV1 import router as LolChallengesV1_router
from src.backend.riotapi.routes.ChampionV3 import router as ChampionV3_router
from src.backend.riotapi.routes.MatchV5 import router as MatchV5_router
from src.backend.riotapi.routes.ChampionMasteryV4 import router as ChampionMasteryV4_router
from src.log.timezone import GetProgramTimezone, GetProgramTimezoneName
from src.utils.static import DAY, RIOTAPI_ENV_CFG_FILE
from src.utils.static import EXTENDED_TTL_DURATION

try:
    import logfire
    logfire.configure(
        send_to_logfire=False,
        show_summary=True,
        trace_sample_rate=0.8,
        collect_system_metrics=True,
    )
except ImportError as e:
    logging.warning(f"Error on importing the LogFire: {e}")
    logfire = None


# import os
# import sys
# print(os.environ["PYTHONPATH"])
# print(sys.path)

# ==================================================================================================
@lru_cache(maxsize=8, typed=True)
def _load_datetime(year: int, month: int, day: int, hour: int, minute: int, second: int, timezone: str) -> datetime:
    return datetime(year=year, month=month, day=day, hour=hour, minute=minute, second=second, tzinfo=ZoneInfo(timezone))


def reload_expiry_time_for_middleware() -> datetime:
    with open(RIOTAPI_ENV_CFG_FILE, 'r') as riotapi_env:
        config = toml.load(riotapi_env)
        deadline_cfg: dict = config['riotapi']['key']['expiry_date']
        tomorrow = datetime.now(tz=GetProgramTimezone()) + timedelta(days=1)
        year: int = deadline_cfg.get('YEAR', tomorrow.year)
        month: int = deadline_cfg.get('MONTH', tomorrow.month)
        day: int = deadline_cfg.get('DAY', tomorrow.day)
        hour: int = deadline_cfg.get('HOUR', tomorrow.hour)
        minute: int = deadline_cfg.get('MINUTE', tomorrow.minute)
        second: int = deadline_cfg.get('SECOND', tomorrow.second)
        timezone: str = deadline_cfg.get('TIMEZONE', GetProgramTimezoneName())
        return _load_datetime(year=year, month=month, day=day, hour=hour, minute=minute, second=second,
                              timezone=timezone)


class RIOTAPI_USER(BaseModel):
    PUUID: str | None = Field(None, title="PUUID", description="The PUUID of the player you want to track")
    USERNAME: str = Field(..., title="Username", description="The username of the player you want to track")
    TAGLINE: str = Field(..., title="Tagline", description="The tagline of the player you want to track")
    REGION: str = Field(..., title="Region", description="The region of the player you want to track")


class USER_CFG(BaseModel):
    REGION: str = Field(..., title="Region", description="The region of the player you want to track")
    TIMEOUT: dict = Field(default_factory=dict, title="Timeout", description="The timeout for the HTTP request")
    AUTH: dict = Field(default_factory=dict, title="Authorization", description="The API key for the Riot API")


def reload_authentication_for_router(application: FastAPI) -> int:
    with open(RIOTAPI_ENV_CFG_FILE, 'r') as riotapi_env:
        config = toml.load(riotapi_env)
        # Set tracking users
        cfg = config["riotapi"]["user"]
        application.default_user = RIOTAPI_USER(**cfg)

        # Set authentication/timeout/... for shared resources
        user_cfg = {
            "REGION": config["riotapi"]["user"]["REGION"],
            "TIMEOUT": config["riotapi"]["httpx_timeout"],
            "AUTH": config["riotapi"]["key"]
        }
        t = USER_CFG(**user_cfg)
        application.default_user_cfg = t

        if hasattr(application, "lst_routers"):
            logging.debug("Reloading the authentication for the routers also ...")
            lst_routers = application.lst_routers
            for rt in lst_routers:
                rt.default_user = application.default_user
                rt.default_user_cfg = t

        # Return the refresh rate for next reload
        return config["riotapi"].get("REFRESH_RATE", 300)  # 5 minutes


@asynccontextmanager
async def riotapi_lifespan(application: ASGIApp | FastAPI):
    # On-Startup
    logging.info("The logging mechanism has been initialized ...")
    MAX_REPETITIONS: int = -1  # -1: infinite loop
    CURRENT_REPETITIONS: int = 0

    async def _reload_dependency_resources():
        nonlocal MAX_REPETITIONS, CURRENT_REPETITIONS
        if MAX_REPETITIONS < -1:
            raise ValueError("The maximum repetitions must be greater than or equal to -1")

        while MAX_REPETITIONS == -1 or CURRENT_REPETITIONS < MAX_REPETITIONS:
            next_trigger: int = reload_authentication_for_router(application)
            await CleanupRiotClient()
            logging.info(f"Reloaded the authentication, and pool cleanup in the {RIOTAPI_ENV_CFG_FILE} file "
                         f"for the resource update")

            if MAX_REPETITIONS != -1:
                CURRENT_REPETITIONS += 1
            if CURRENT_REPETITIONS != MAX_REPETITIONS and next_trigger > 0:
                logging.info(f"The next reload will be triggered in the next {next_trigger} seconds ...")
                await asyncio.sleep(next_trigger)

    # Don't push await for daemon task
    loop = asyncio.get_event_loop()
    loop.create_task(_reload_dependency_resources(), name="Reload Dependency Resources") # pragma: no cover

    # Application Initialization
    logging.info("Starting the application ...")
    yield

    # Clean up and release the resources
    await CleanupRiotClient()
    MAX_REPETITIONS = CURRENT_REPETITIONS  # Stop the loop
    logging.info("Safely shutting down the application. The HTTPS connection is cleanup ...")
    logging.shutdown()
    try:
        import logfire
        logfire.shutdown()
    except ImportError as e:
        logging.warning(f"Error on importing the LogFire: {e}")


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
logging.info("The FastAPI application has been initialized. Adding the middlewares ...")
SECRET_KEY = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY, max_age=DAY, https_only=False)  # 1-day session
app.add_middleware(ExpiryTimeMiddleware, deadline=reload_expiry_time_for_middleware)
with open(RIOTAPI_ENV_CFG_FILE, 'r') as riotapi_environment_global:
    config = toml.load(riotapi_environment_global)
    cfg = config["riotapi"]["limit"]["global"]
    # Set global rate limit
    for _, value in cfg.items():
        MAX_REQUESTS: int = value["MAX_REQUESTS"]
        REQUESTS_INTERVAL: int = value["REQUESTS_INTERVAL"]
        app.add_middleware(RateLimiterMiddleware, max_requests=MAX_REQUESTS, interval_by_second=REQUESTS_INTERVAL)
# app.add_middleware(ReworkedApitallyMiddleware, unmonitored_paths=["/docs", "/redoc", "/openapi.json"],
#                    identify_consumer_callback=None)
logging.info("The middlewares have been added to the application ...")

# ==================================================================================================
logging.info("Including the routers in the application ...")
APIROUTER_MAPPING: dict[str, APIRouter] = {
    "/Account/v1": AccountV1_router,
    "/LolChallenges/v1": LolChallengesV1_router,
    "/Match/v5": MatchV5_router,
    "/ChampionMastery/v4": ChampionMasteryV4_router,
    "/Champion/v3": ChampionV3_router,
}
for path, router in APIROUTER_MAPPING.items():
    app.include_router(router, prefix=path)
app.lst_routers = [r for _, r in APIROUTER_MAPPING.items()]
logging.info("The routers have been included in the application, adding the dependency resource is done ...")

# ==================================================================================================
# Initiate the LogFire
logging.info("The LogFire has been initialized ...")
if logfire is not None:
    logfire.instrument_fastapi(app)


# ==================================================================================================
@app.get("/_health", tags=["health"], response_model=dict[str, str])
async def root():
    return {"message": "Hello World. Your application can now be accessed at /docs or /redoc."}

@ttl_cache(maxsize=1, ttl=EXTENDED_TTL_DURATION)
@app.get("/tags", tags=["tags"], response_model=dict[str, list[str]])
async def export() -> dict[str, list[str]]:
    tags: dict[str, list[str]] = {}
    for route in app.routes:
        if hasattr(route, "tags") and hasattr(route, "path"):
            tags[route.path] = route.tags
    return tags
