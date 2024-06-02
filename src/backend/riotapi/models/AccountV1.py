from pydantic import BaseModel, Field

class AccountDto(BaseModel):
    puuid: str = Field(..., title="PUUID", description="The PUUID of the player you want to track")
    gameName: str = Field(..., title="Player Name", description="The player's name of the player you want to track")
    tagLine: str = Field(..., title="Tagline", description="The tagline of the player you want to track")


class ActiveShardDto(BaseModel):
    puuid: str = Field(..., title="PUUID", description="The PUUID of the player you want to track")
    game: str = Field(..., title="Game", description="The game of the player you want to track")
    ap: str = Field(..., title="Active Shard", description="The active shard of the player you want to track")

