import asyncio
import logging
import random
import string
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from time import perf_counter
from zoneinfo import ZoneInfo

import toml
from cachetools.func import ttl_cache
from fastapi import FastAPI, APIRouter
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.types import ASGIApp
from starlette.routing import Route

from src.backend.riotapi.client import HttpxAsyncClient
from src.backend.riotapi.middlewares.LocalMiddleware import (ExpiryDateMiddleware, RateLimitMiddleware,
                                                             HeaderHardeningMiddleware)
# from src.backend.riotapi.routes.AccountV1 import router as AccountV1_router
# from src.backend.riotapi.routes.LolChallengesV1 import router as LolChallengesV1_router
# from src.backend.riotapi.routes.ChampionV3 import router as ChampionV3_router
# from src.backend.riotapi.routes.MatchV5 import router as MatchV5_router
# from src.backend.riotapi.routes.ChampionMasteryV4 import router as ChampionMasteryV4_router
from src.backend.riotapi.inapp import DefaultSettings
from src.log.timezone import GetProgramTimezone, GetProgramTimezoneName
from src.static.static import (DAY, RIOTAPI_ENV_CFG_FILE, BASE_TTL_ENTRY, BASE_TTL_DURATION, EXTENDED_TTL_DURATION,
                               REFRESH_RATE_IF_NOT_FOUND, MIN_REFRESH_RATE_IF_FOUND, RIOTAPI_SECRETS_CFG_FILE)
from src.static.static import CREDENTIALS


# ==================================================================================================
# Use TTL Cache with Expiry Time to Refresh the Middleware automatically
@ttl_cache(maxsize=BASE_TTL_ENTRY, ttl=BASE_TTL_DURATION, timer=perf_counter, typed=True)
def ReloadExpiryTimeForMiddleware() -> datetime:
    with open(RIOTAPI_ENV_CFG_FILE, 'r') as riotapi_env:
        deadline_cfg: dict = toml.load(riotapi_env)['riotapi']['expiry_date']
        tomorrow = datetime.now(tz=GetProgramTimezone()) + timedelta(days=1)
        year: int = deadline_cfg.get('YEAR', tomorrow.year)
        month: int = deadline_cfg.get('MONTH', tomorrow.month)
        day: int = deadline_cfg.get('DAY', tomorrow.day)
        hour: int = deadline_cfg.get('HOUR', tomorrow.hour)
        minute: int = deadline_cfg.get('MINUTE', tomorrow.minute)
        second: int = deadline_cfg.get('SECOND', tomorrow.second)
        timezone: str = deadline_cfg.get('TIMEZONE', GetProgramTimezoneName())

        return datetime(year=year, month=month, day=day, hour=hour, minute=minute, second=second,
                        tzinfo=ZoneInfo(timezone))


def ReloadAuthenticationForRouter(application: FastAPI) -> int:
    with open(RIOTAPI_ENV_CFG_FILE, 'r') as riotapi_env:
        with open(RIOTAPI_SECRETS_CFG_FILE, 'r') as riotapi_secret:
            env_config = toml.load(riotapi_env)["riotapi"]["default"]
            secret_config = toml.load(riotapi_secret)["riotapi"]

            # Set default value
            dft: dict = {
                "REGION": env_config["REGION"],
                "CONTINENT": env_config["CONTINENT"],
                "LOCALE": env_config["LOCALE"],
                "TIMEOUT": env_config["httpx_timeout"],
                "AUTH": {cred: secret_config[cred]["key"] for key, cred in CREDENTIALS.__members__.items()
                         if cred in secret_config}
            }
            if env_config.get("MATCH_CONTINENT", None) is None:
                dft["MATCH_CONTINENT"] = dft["CONTINENT"]
                if dft["CONTINENT"] == "ASIA":
                    dft["MATCH_CONTINENT"] = "SEA"
            else:
                dft["MATCH_CONTINENT"] = env_config["MATCH_CONTINENT"]

            default: DefaultSettings = DefaultSettings(**dft)
            application.inapp_default = default
            if hasattr(application, "lst_routers"):
                logging.debug("Reloading the authentication for the routers also ...")
                lst_routers = application.lst_routers
                for rt in lst_routers:
                    rt.inapp_default = default

        # Return the refresh rate for next reload
        return min(REFRESH_RATE_IF_NOT_FOUND, env_config.get("REFRESH_RATE", MIN_REFRESH_RATE_IF_FOUND))


@asynccontextmanager
async def RiotapiLifespan(application: ASGIApp | FastAPI):
    # On-Startup
    logging.info("The logging mechanism has been initialized ...")
    MAX_REPETITIONS: int = -1  # -1: infinite loop
    CURRENT_REPETITIONS: int = 0

    async def _ReloadDependencyResources():
        nonlocal MAX_REPETITIONS, CURRENT_REPETITIONS
        if MAX_REPETITIONS < -1:
            raise ValueError("The maximum repetitions must be greater than or equal to -1")

        while MAX_REPETITIONS == -1 or CURRENT_REPETITIONS < MAX_REPETITIONS:
            next_trigger: int = ReloadAuthenticationForRouter(application)
            await HttpxAsyncClient.CleanUpPool()
            logging.info(f"Reloaded the authentication and pool cleanup in the {RIOTAPI_ENV_CFG_FILE} file "
                         f"for the resource update")

            if MAX_REPETITIONS != -1:
                CURRENT_REPETITIONS += 1
            if CURRENT_REPETITIONS != MAX_REPETITIONS and next_trigger > 0:
                logging.info(f"The next reload will be triggered in the next {next_trigger} seconds ...")
                await asyncio.sleep(next_trigger)

    # Don't push await for daemon task
    loop = asyncio.get_event_loop()
    loop.create_task(_ReloadDependencyResources(), name="Reload Dependency Resources") # pragma: no cover

    # Application Initialization
    logging.info("Starting the application ...")
    yield

    # Clean up and release the resources
    MAX_REPETITIONS = CURRENT_REPETITIONS  # Stop the loop
    await HttpxAsyncClient.CleanUpPool()
    logging.info("Safely shutting down the application. The HTTPS connection is cleanup ...")
    logging.shutdown()


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
    'LIFESPAN': RiotapiLifespan,
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
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY, max_age=DAY, same_site='lax',
                   https_only=False)  # 1-day session
app.add_middleware(GZipMiddleware, minimum_size=2**10)
app.add_middleware(ExpiryDateMiddleware, deadline=ReloadExpiryTimeForMiddleware)
app.add_middleware(HeaderHardeningMiddleware)

with open(RIOTAPI_ENV_CFG_FILE, 'r') as riotapi_environment_global:
    config = toml.load(riotapi_environment_global)
    cfg = config["riotapi"]["limit"]
    # Set global rate limit
    for _, value in cfg.items():
        MAX_REQUESTS: int = value["MAX_REQUESTS"]
        REQUESTS_INTERVAL: int = value["REQUESTS_INTERVAL"]
        app.add_middleware(RateLimitMiddleware,
                           max_requests=MAX_REQUESTS, interval_by_second=REQUESTS_INTERVAL)
# _app.add_middleware(MonitorMiddleware, unmonitored_paths=["/docs", "/redoc", "/openapi.json"],
#                    identify_consumer_callback=None)
logging.info("The middlewares have been added to the application ...")

# ==================================================================================================
logging.info("Including the routers in the application ...")
APIROUTER_MAPPING: dict[str, APIRouter] = {
    # "/Account/v1": AccountV1_router,
    # "/LolChallenges/v1": LolChallengesV1_router,
    # "/Match/v5": MatchV5_router,
    # "/ChampionMastery/v4": ChampionMasteryV4_router,
    # "/Champion/v3": ChampionV3_router,
}
for path, router in APIROUTER_MAPPING.items():
    app.include_router(router, prefix=path)
app.lst_routers = [r for _, r in APIROUTER_MAPPING.items()]
logging.info("The routers have been included in the application, adding the dependency resource is done ...")

# ==================================================================================================
@app.get("/_health", tags=["health"], response_model=dict[str, str])
async def root():
    return {"message": "Hello World. Your application can now be accessed at /docs or /redoc."}


@ttl_cache(maxsize=1, ttl=EXTENDED_TTL_DURATION)
@app.get("/_tags", tags=["tags"], response_model=dict[str, list[str]])
async def export() -> dict[str, list[str]]:
    tags: dict[str, list[str]] = {}
    for route in app.routes:
        assert isinstance(route, Route)
        if hasattr(route, "tags") and hasattr(route, "path"):
            tags[route.path] = route.tags
    return tags
