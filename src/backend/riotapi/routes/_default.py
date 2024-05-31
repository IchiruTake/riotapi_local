from pydantic import BaseModel, Field

from src.backend.riotapi.routes._region import REGION_ANNOTATED_PATTERN


class DefaultSettings(BaseModel):
    region: str = Field(..., title="Region", description="The region of the player you want to track",
                        pattern=REGION_ANNOTATED_PATTERN)
