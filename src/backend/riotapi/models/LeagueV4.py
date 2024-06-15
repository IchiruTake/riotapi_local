from pydantic import BaseModel, Field
from src.backend.riotapi.models.LeagueExpV4 import MiniSeriesDTO, LeagueEntryDTO


class LeagueItemDTO(BaseModel):
    freshBlood: bool
    wins: int = Field(description='Winning team on Summoners Rift.')
    miniSeries: MiniSeriesDTO
    inactive: bool
    veteran: bool
    hotStreak: bool
    rank: str
    leaguePoints: int
    losses: int = Field(description='Losing team on Summoners Rift.')
    summonerId: str = Field(description="Player's encrypted summonerId.")


class LeagueListDTO(BaseModel):
    # Consistently looking up league ids that don't exist will result in a blacklist.
    leagueId: str
    entries: list[LeagueItemDTO]
    tier: str
    name: str
    queue: str
