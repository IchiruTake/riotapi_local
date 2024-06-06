from pydantic import BaseModel, Field

from src.utils.static import REGION_ANNOTATED_PATTERN, CONTINENT_ANNOTATED_PATTERN


class DefaultSettings(BaseModel):
    region: str = Field("VN2", title="Region", description="The default region",
                        pattern=REGION_ANNOTATED_PATTERN)
    continent: str = Field("ASIA", title="Continent", description="The default continent",
                           pattern=CONTINENT_ANNOTATED_PATTERN)
    locale: str = Field("en_US", title="Locale", description="The default locale")
    timeout: dict = Field(default_factory=dict, title="Timeout", description="The default timeout for the HTTP request")
    auth: dict[str, dict] = Field(default_factory=dict, title="Authentication",
                                  description="The API key for the Riot API")

    def GetAuthOfKeyName(self, key_name: str) -> dict | None:
        return self.auth.get(key_name, None)

