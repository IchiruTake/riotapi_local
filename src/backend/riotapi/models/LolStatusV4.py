from pydantic import BaseModel, Field


class ContentDto(BaseModel):
    locale: str
    content: str

class UpdateDto(BaseModel):
    id: int
    author: str
    publish: bool
    publish_locations: list[str] = Field(description='(Legal values: riotclient, riotstatus, game)')
    translations: list[ContentDto]
    created_at: str
    updated_at: str


class StatusDto(BaseModel):
    id: int
    maintenance_status: str = Field(description='(Legal values: scheduled, in_progress, complete)')
    incident_severity: str = Field(description='(Legal values: info, warning, critical)')
    titles: list[ContentDto]
    updates: list[UpdateDto]
    created_at: str
    archive_at: str
    updated_at: str
    platforms: list[str] = Field(description='(Legal values: windows, macos, android, ios, ps4, xbone, switch)')


class PlatformDataDto(BaseModel):
    id: str
    name: str
    locales: list[str]
    maintenances: list[StatusDto]
    incidents: list[StatusDto]
