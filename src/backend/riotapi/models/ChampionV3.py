from pydantic import BaseModel

class ChampionInfo(BaseModel):
    maxNewPlayerLevel: int
    freeChampionIdsForNewPlayers: list[int]
    freeChampionIds: list[int]
