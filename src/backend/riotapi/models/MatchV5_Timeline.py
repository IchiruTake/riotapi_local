"""
See here for updates:
https://github.com/RiotGames/developer-relations/issues/928
https://github.com/RiotGames/developer-relations/issues/754
"""

from pydantic import BaseModel, Field

class MetadataTimeLineDto(BaseModel):
    dataVersion: str = Field(..., description="Match data version.")
    matchId: str = Field(..., description="Match id.")
    participants: list[str] = Field(..., description="A list of participant PUUIDs.")


class ParticipantTimeLineDto(BaseModel):
    participantId: int
    puuid: str


class EventsTimeLineDto(BaseModel):
    timestamp: int
    realTimestamp: int
    type: str


class ChampionStatsDto(BaseModel):
    abilityHaste: int
    abilityPower: int
    armor: int
    armorPen: int
    armorPenPercent: int
    attackDamage: int
    attackSpeed: int
    bonusArmorPenPercent: int
    bonusMagicPenPercent: int
    ccReduction: int
    cooldownReduction: int
    health: int
    healthMax: int
    healthRegen: int
    lifesteal: int
    magicPen: int
    magicPenPercent: int
    magicResist: int
    movementSpeed: int
    omnivamp: int
    physicalVamp: int
    power: int
    powerMax: int
    powerRegen: int
    spellVamp: int

class DamageStatsDto(BaseModel):
    magicDamageDone: int
    magicDamageDoneToChampions: int
    magicDamageTaken: int
    physicalDamageDone: int
    physicalDamageDoneToChampions: int
    physicalDamageTaken: int
    totalDamageDone: int
    totalDamageDoneToChampions: int
    totalDamageTaken: int
    trueDamageDone: int
    trueDamageDoneToChampions: int
    trueDamageTaken: int

class PositionDto(BaseModel):
    x: int
    y: int


class ParticipantFrameDto(BaseModel):
    championStats: ChampionStatsDto
    currentGold: int
    damageStats: DamageStatsDto
    goldPerSecond: int
    jungleMinionsKilled: int
    level: int
    minionsKilled: int
    participantId: int
    position: PositionDto
    timeEnemySpentControlled: int
    totalGold: int
    xp: int

class ParticipantFramesDto(BaseModel):
    p01: ParticipantFrameDto = Field(alias="1")
    p02: ParticipantFrameDto = Field(alias="2")
    p03: ParticipantFrameDto = Field(alias="3")
    p04: ParticipantFrameDto = Field(alias="4")
    p05: ParticipantFrameDto = Field(alias="5")
    p06: ParticipantFrameDto = Field(alias="6")
    p07: ParticipantFrameDto = Field(alias="7")
    p08: ParticipantFrameDto = Field(alias="8")
    p09: ParticipantFrameDto = Field(alias="9")
    p10: ParticipantFrameDto = Field(alias="10")

class FramesTimeLineDto(BaseModel):
    events: EventsTimeLineDto
    participantFrames: ParticipantFramesDto
    timestamp: int


class InfoTimeLineDto(BaseModel):
    endOfGameResult: str = Field(..., description="Refer to indicate if the game ended in termination.")
    frameInterval: int = Field(..., description="The interval in seconds at which frames are created.")
    gameId: int = Field(..., description="Game ID.")
    participants: list[ParticipantTimeLineDto]
    frames: list[FramesTimeLineDto]


class TimeLineDto(BaseModel):
    metadata: MetadataTimeLineDto
    info: InfoTimeLineDto

