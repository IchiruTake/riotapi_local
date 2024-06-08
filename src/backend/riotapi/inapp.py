from typing import Annotated, Callable
from pydantic import BaseModel, Field
from fastapi import Path, Query
from src.static.static import (REGION_ANNOTATED_PATTERN, NORMAL_CONTINENT_ANNOTATED_PATTERN,
                               MATCH_CONTINENT_ANNOTATED_PATTERN)


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
