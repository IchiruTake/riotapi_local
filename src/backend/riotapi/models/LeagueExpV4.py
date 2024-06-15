from pydantic import BaseModel, Field

class MiniSeriesDTO(BaseModel):
    losses: int
    progress: str
    target: int
    wins: int


class LeagueEntryDTO(BaseModel):
    leagueId: str
    summonerId: str = Field(description="Player's summonerId (Encrypted)")
    queueType: str
    tier: str
    rank: str = Field(description="The player's division within a tier.")
    leaguePoints: int
    wins: int = Field(description="Winning team on Summoners Rift. First placement in Teamfight Tactics.")
    losses: int = Field(description="Losing team on Summoners Rift. Second through eighth placement in "
                                    "Teamfight Tactics.")
    hotStreak: bool
    veteran: bool
    freshBlood: bool
    inactive: bool
    miniSeries: MiniSeriesDTO

