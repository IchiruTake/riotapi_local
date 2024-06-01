from pydantic import BaseModel, Field

from src.backend.riotapi.routes._region import REGION_ANNOTATED_PATTERN


class DefaultSettings(BaseModel):
    region: str = Field("VN2", title="Region", description="The region of the player you want to track",
                        pattern=REGION_ANNOTATED_PATTERN)
    timeout: dict = Field(default_factory=dict, title="Timeout", description="The timeout for the HTTP request")
    auth: dict = Field(default_factory=dict, title="Authentication", description="The API key for the Riot API")

    def GetAuthOfKeyName(self, key_name: str) -> str:
        return self.auth[key_name]
