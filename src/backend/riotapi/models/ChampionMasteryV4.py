from pydantic import BaseModel, Field


class ChampionMasteryDto(BaseModel):
    puuid: str = Field(..., title="PUUID", description="The PUUID of the player you want to track", max_length=78,
                       frozen=True)
    championId: int = Field(..., description="Champion ID for this entry.")
    championLevel: int = Field(..., description="Champion level for specified player and champion combination.")
    championPoints: int = Field(...,
                                description="Total number of champion points for this player and champion combination "
                                            "- they are used to determine championLevel.")
    lastPlayTime: int = Field(..., description="Last time this champion was played by this player - in Unix "
                                               "seconds time format.")
    championPointsSinceLastLevel: int = Field(..., description="Number of points earned since current level "
                                                               "has been achieved.")
    championPointsUntilNextLevel: int = Field(...,
                                              description="Number of points needed to achieve next level. Zero if "
                                                          "player reached maximum champion level for this champion.")
    chestGranted: bool = Field(..., description="Is chest granted for this champion or not in current season.")
    tokensEarned: int = Field(..., description="The token earned for this champion at the current championLevel. "
                                               "When the championLevel is advanced the tokensEarned resets to 0.")
    summonerId: str = Field(..., description="Summoner ID for this entry. (Encrypted)", frozen=True)
