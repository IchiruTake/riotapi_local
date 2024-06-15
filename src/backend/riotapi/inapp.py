from pprint import pformat

import toml
import logging
from pydantic import BaseModel, Field
from src.static.static import (REGION_ANNOTATED_PATTERN, NORMAL_CONTINENT_ANNOTATED_PATTERN, RIOTAPI_ENV_CFG_FILE,
                               MATCH_CONTINENT_ANNOTATED_PATTERN, REGION_TTL_MULTIPLIER, CONTINENT_TTL_MULTIPLIER)
from fastapi.routing import APIRouter
from functools import lru_cache


class DefaultSettings(BaseModel):
    region: str = Field("VN2", title="Region", alias="REGION",
                        pattern=REGION_ANNOTATED_PATTERN)
    continent: str = Field("ASIA", title="Continent", alias="CONTINENT",
                           pattern=NORMAL_CONTINENT_ANNOTATED_PATTERN)
    match_continent: str = Field("SEA", title="Match Continent", alias="MATCH_CONTINENT",
                                 pattern=MATCH_CONTINENT_ANNOTATED_PATTERN)
    locale: str = Field("en_US", title="Locale", alias="LOCALE",
                        description="The default locale")
    timeout: dict = Field(default_factory=dict, title="Timeout", alias="TIMEOUT",
                          description="The default timeout for the HTTP request")
    auth: dict[str, dict] = Field(default_factory=dict, title="Authentication", alias="AUTH", allow_mutation=True,
                                  description="The API key for the Riot API")

    def GetAuthOfKeyName(self, key_name: str) -> dict | None:
        return self.auth.get(key_name, None)


class CustomAPIRouter(APIRouter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.inapp_default: DefaultSettings | None = None
        self.entry_scale: bool = True
        self.entry_exponential_scale: bool = False
        self.duration_scale: bool = False
        self.duration_exponential_scale: bool = False

    def load_profile(self, name: str, toml_file: str = RIOTAPI_ENV_CFG_FILE, ) -> None:
        with open(toml_file, "r") as toml_stream:
            profile = toml.load(toml_stream).get("riotapi", {}).get("routers", {}).get(name, {})
            for key in name.split('.'):
                profile = profile.get(key, {})
                if not profile:
                    logging.warning(f"The wanted profile as requested ({name}) is not found in the TOML file.")
                    return
            logging.info(f"Loading profile {name} successfully: {pformat(profile)}")
            self.entry_scale = profile.get("ENTRY_SCALE", self.entry_scale)
            self.entry_exponential_scale = profile.get("ENTRY_EXP_SCALE", self.entry_exponential_scale)
            self.duration_scale = profile.get("DURATION_SCALE", self.duration_scale)
            self.duration_exponential_scale = profile.get("DURATION_EXP_SCALE", self.duration_exponential_scale)

    @staticmethod
    def _scale(unit: int, region_path: bool, num_params: int = 1, scale_mode: bool = False,
               exponential_mode: bool = False) -> int:
        if not scale_mode:
            return unit

        multiplier: int = max(1, REGION_TTL_MULTIPLIER if region_path else CONTINENT_TTL_MULTIPLIER)
        if not exponential_mode:
            return unit * multiplier

        return unit * (multiplier ** num_params)

    @lru_cache(maxsize=1024, typed=True)
    def scale(self, maxsize: int, ttl: int, region_path: bool, num_params: int = 1) -> tuple[int, int]:
        maxsize = self._scale(maxsize, region_path, num_params, self.entry_scale, self.entry_exponential_scale)
        ttl = self._scale(ttl, region_path, num_params, self.duration_scale, self.duration_exponential_scale)
        return maxsize, ttl
