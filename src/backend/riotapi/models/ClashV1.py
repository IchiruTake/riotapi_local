from pydantic import BaseModel, Field

class PlayerDto(BaseModel):
    summonerId: str
    teamId: str
    position: str = Field(..., description="(Legal values: UNSELECTED, FILL, TOP, JUNGLE, MIDDLE, BOTTOM, UTILITY)")
    role: str = Field(..., description="(Legal values: CAPTAIN, MEMBER)")

class TeamDto(BaseModel):
    id: str
    tournamentId: int
    name: str
    iconId: int
    tier: int
    captain: str = Field(..., description="Summoner ID of the team captain.")
    abbreviation: str
    players: list[PlayerDto] = Field(..., description="Team members.")


class TournamentPhaseDto(BaseModel):
    id: int
    registrationTime: int
    startTime: int
    cancelled: bool


class TournamentDto(BaseModel):
    id: int
    themeId: int
    nameKey: str
    nameKeySecondary: str
    schedule: list[TournamentPhaseDto] = Field(..., description="Tournament phase.")

