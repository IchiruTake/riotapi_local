"""
See here for updates:
https://github.com/RiotGames/developer-relations/issues/928
https://github.com/RiotGames/developer-relations/issues/754
"""

from pydantic import BaseModel, Field

class MetadataDto(BaseModel):
    dataVersion: str = Field(..., description="Match data version.")
    matchId: str = Field(..., description="Match id.")
    participants: list[str] = Field(..., description="A list of participant PUUIDs.")


class MissionsDto(BaseModel):
    playerScore0: int
    playerScore1: int
    playerScore2: int
    playerScore3: int
    playerScore4: int
    playerScore5: int
    playerScore6: int
    playerScore7: int
    playerScore8: int
    playerScore9: int
    playerScore10: int
    playerScore11: int


class ObjectiveDto(BaseModel):
    first: bool
    kills: int


class ObjectivesDto(BaseModel):
    baron: ObjectiveDto
    champion: ObjectiveDto
    dragon: ObjectiveDto
    horde: ObjectiveDto
    inhibitor: ObjectiveDto
    riftHerald: ObjectiveDto
    tower: ObjectiveDto


class BanDto(BaseModel):
    championId: int
    pickTurn: int


class TeamDto(BaseModel):
    bans: list[BanDto]
    objectives: ObjectivesDto
    teamId: int
    win: bool


class PerkStyleSelectionDto(BaseModel):
    perk: int
    var1: int
    var2: int
    var3: int


class PerkStyleDto(BaseModel):
    description: str
    selections: list[PerkStyleSelectionDto]
    style: int


class PerkStatsDto(BaseModel):
    defense: int
    flex: int
    offense: int


class PerksDto(BaseModel):
    statPerks: PerkStatsDto
    styles: list[PerkStyleDto]


class ChallengesDto(BaseModel):
    assistStreakCount12: int = Field(default=None, alias="12AssistStreakCount",
                                     description="Placeholder for 12AssistStreakCount.")
    abilityUses: int
    acesBefore15Minutes: int
    alliedJungleMonsterKills: int
    baronTakedowns: int
    blastConeOppositeOpponentCount: int
    bountyGold: int
    buffsStolen: int
    completeSupportQuestInTime: int
    controlWardsPlaced: int
    damagePerMinute: float
    damageTakenOnTeamPercentage: float
    dancedWithRiftHerald: int
    deathsByEnemyChamps: int
    dodgeSkillShotsSmallWindow: int
    doubleAces: int
    dragonTakedowns: int
    legendaryItemUsed: list[int]
    effectiveHealAndShielding: float
    elderDragonKillsWithOpposingSoul: int
    elderDragonMultikills: int
    enemyChampionImmobilizations: int
    enemyJungleMonsterKills: int
    epicMonsterKillsNearEnemyJungler: int
    epicMonsterKillsWithin30SecondsOfSpawn: int
    epicMonsterSteals: int
    epicMonsterStolenWithoutSmite: int
    firstTurretKilled: int
    firstTurretKilledTime: float | None = Field(None)
    flawlessAces: int
    fullTeamTakedown: int
    gameLength: float
    getTakedownsInAllLanesEarlyJungleAsLaner: int
    goldPerMinute: float
    hadOpenNexus: int
    immobilizeAndKillWithAlly: int
    initialBuffCount: int
    initialCrabCount: int
    jungleCsBefore10Minutes: int
    junglerTakedownsNearDamagedEpicMonster: int
    kda: float
    killAfterHiddenWithAlly: int
    killedChampTookFullTeamDamageSurvived: int
    killingSprees: int
    killParticipation: float
    killsNearEnemyTurret: int
    killsOnOtherLanesEarlyJungleAsLaner: int
    killsOnRecentlyHealedByAramPack: int
    killsUnderOwnTurret: int
    killsWithHelpFromEpicMonster: int
    knockEnemyIntoTeamAndKill: int
    kTurretsDestroyedBeforePlatesFall: int
    landSkillShotsEarlyGame: int
    laneMinionsFirst10Minutes: int
    lostAnInhibitor: int
    maxKillDeficit: int
    mejaisFullStackInTime: int
    moreEnemyJungleThanOpponent: int
    multiKillOneSpell: int
    multikills: int
    multikillsAfterAggressiveFlash: int
    multiTurretRiftHeraldCount: int
    outerTurretExecutesBefore10Minutes: int
    outnumberedKills: int
    outnumberedNexusKill: int
    perfectDragonSoulsTaken: int
    perfectGame: int
    pickKillWithAlly: int
    poroExplosions: int
    quickCleanse: int
    quickFirstTurret: int
    quickSoloKills: int
    riftHeraldTakedowns: int
    saveAllyFromDeath: int
    scuttleCrabKills: int
    shortestTimeToAceFromFirstTakedown: float | None = Field(None)
    skillshotsDodged: int
    skillshotsHit: int
    snowballsHit: int
    soloBaronKills: int
    soloKills: int
    stealthWardsPlaced: int
    survivedSingleDigitHpCount: int
    survivedThreeImmobilizesInFight: int
    takedownOnFirstTurret: int
    takedowns: int
    takedownsAfterGainingLevelAdvantage: int
    takedownsBeforeJungleMinionSpawn: int
    takedownsFirstXMinutes: int
    takedownsInAlcove: int
    takedownsInEnemyFountain: int
    teamBaronKills: int
    teamDamagePercentage: float
    teamElderDragonKills: int
    teamRiftHeraldKills: int
    tookLargeDamageSurvived: int
    turretPlatesTaken: int
    turretsTakenWithRiftHerald: int
    turretTakedowns: int
    twentyMinionsIn3SecondsCount: int
    twoWardsOneSweeperCount: int
    unseenRecalls: int
    visionScorePerMinute: int | float
    wardsGuarded: int
    wardTakedowns: int
    wardTakedownsBefore20M: int


class ParticipantDto(BaseModel):
    allInPings: int
    assistMePings: int
    assists: int
    baronKills: int
    bountyLevel: int
    champExperience: int
    champLevel: int
    championId: int = Field(..., description="""
    Prior to patch 11.4, on Feb 18th, 2021, this field returned invalid championIds. We recommend determining the 
    champion based on the championName field for matches played prior to patch 11.4.""")
    championName: str
    commandPings: int
    championTransform: int = Field(..., description="""
    This field is currently only utilized for Kayn's transformations. (Legal values: 0 - None, 1 - Slayer, 
    2 - Assassin)""")
    consumablesPurchased: int
    challenges: ChallengesDto
    damageDealtToBuildings: int
    damageDealtToObjectives: int
    damageDealtToTurrets: int
    dangerPings: int
    damageSelfMitigated: int
    deaths: int
    detectorWardsPlaced: int
    doubleKills: int
    dragonKills: int
    eligibleForProgression: bool
    enemyMissingPings: int
    enemyVisionPings: int
    firstBloodAssist: bool
    firstBloodKill: bool
    firstTowerAssist: bool
    firstTowerKill: bool
    gameEndedInEarlySurrender: bool
    gameEndedInSurrender: bool
    holdPings: int
    getBackPings: int
    goldEarned: int
    goldSpent: int
    individualPosition: str = Field(..., description="""
    Both individualPosition and teamPosition are computed by the game server and are different versions of the most 
    likely position played by a player. The individualPosition is the best guess for which position the player actually 
    played in isolation of anything else. The teamPosition is the best guess for which position the player actually 
    played if we add the constraint that each team must have one top player, one jungle, one middle, etc. Generally the 
    recommendation is to use the teamPosition field over the individualPosition field.""")
    inhibitorKills: int
    inhibitorTakedowns: int
    inhibitorsLost: int
    item0: int
    item1: int
    item2: int
    item3: int
    item4: int
    item5: int
    item6: int
    itemsPurchased: int
    killingSprees: int
    kills: int
    lane: str
    largestCriticalStrike: int
    largestKillingSpree: int
    largestMultiKill: int
    longestTimeSpentLiving: int
    magicDamageDealt: int
    magicDamageDealtToChampions: int
    magicDamageTaken: int
    missions: MissionsDto
    neutralMinionsKilled: int
    needVisionPings: int
    nexusKills: int
    nexusTakedowns: int
    nexusLost: int
    objectivesStolen: int
    objectivesStolenAssists: int
    onMyWayPings: int
    participantId: int
    pentaKills: int
    perks: PerksDto
    physicalDamageDealt: int
    physicalDamageDealtToChampions: int
    physicalDamageTaken: int
    placement: int
    playerAugment1: int
    playerAugment2: int
    playerAugment3: int
    playerAugment4: int
    playerSubteamId: int
    pushPings: int
    profileIcon: int
    puuid: str
    quadraKills: int
    riotIdGameName: str
    riotIdName: str | None = Field(None, description="This field is currently not utilized.")
    riotIdTagline: str
    role: str
    sightWardsBoughtInGame: int
    spell1Casts: int
    spell2Casts: int
    spell3Casts: int
    spell4Casts: int
    subteamPlacement: int
    summoner1Casts: int
    summoner1Id: int
    summoner2Casts: int
    summoner2Id: int
    summonerId: str
    summonerLevel: int
    summonerName: str
    teamEarlySurrendered: bool
    teamId: int
    teamPosition: str = Field(..., description="""
    Both individualPosition and teamPosition are computed by the game server and are different versions of the most 
    likely position played by a player. The individualPosition is the best guess for which position the player actually 
    played in isolation of anything else. The teamPosition is the best guess for which position the player actually 
    played if we add the constraint that each team must have one top player, one jungle, one middle, etc. Generally the 
    recommendation is to use the teamPosition field over the individualPosition field.""")
    timeCCingOthers: int
    timePlayed: int
    totalAllyJungleMinionsKilled: int
    totalDamageDealt: int
    totalDamageDealtToChampions: int
    totalDamageShieldedOnTeammates: int
    totalDamageTaken: int
    totalEnemyJungleMinionsKilled: int
    totalHeal: int
    totalHealsOnTeammates: int
    totalMinionsKilled: int
    totalTimeCCDealt: int
    totalTimeSpentDead: int
    totalUnitsHealed: int
    tripleKills: int
    trueDamageDealt: int
    trueDamageDealtToChampions: int
    trueDamageTaken: int
    turretKills: int
    turretTakedowns: int
    turretsLost: int
    unrealKills: int
    visionScore: int
    visionClearedPings: int
    visionWardsBoughtInGame: int
    wardsKilled: int
    wardsPlaced: int
    win: bool


class InfoDto(BaseModel):
    endOfGameResult: str = Field(..., description="Refer to indicate if the game ended in termination.")
    gameCreation: int = Field(..., description="Unix timestamp for when the game is created on the game server "
                                               "(i.e., the loading screen).")
    gameDuration: int = Field(..., description="""
    Prior to patch 11.20, this field returns the game length in milliseconds calculated from gameEndTimestamp - 
    gameStartTimestamp. Post patch 11.20, this field returns the max timePlayed of any participant in the game in 
    seconds, which makes the behavior of this field consistent with that of match-v4. The best way to handling the 
    change in this field is to treat the value as milliseconds if the gameEndTimestamp field isn't in the response and 
    to treat the value as seconds if gameEndTimestamp is in the response..""")
    gameEndTimestamp: int = Field(..., description="""
    Unix timestamp for when match ends on the game server. This timestamp can occasionally be significantly longer than 
    when the match "ends". The most reliable way of determining the timestamp for the end of the match would be to add 
    the max time played of any participant to the gameStartTimestamp. This field was added to match-v5 in patch 11.20 
    on Oct 5th, 2021.
    """)
    gameId: int = Field(..., description="Game ID.")
    gameMode: str = Field(..., description="Refer to the Game Constants documentation.")
    gameName: str = Field(..., description="Game name.")
    gameStartTimestamp: int = Field(..., description="Unix timestamp for when match starts on the game server.")
    gameType: str = Field(..., description="Refer to the Game Constants documentation.")
    gameVersion: str = Field(..., description="The first two parts can be used to determine the patch a game "
                                              "was played on.")
    mapId: int = Field(..., description="Refer to the Game Constants documentation.")
    participants: list[ParticipantDto]
    platformId: str = Field(..., description="Platform where the match was played.")
    queueId: int = Field(..., description="Refer to the Game Constants documentation.")
    teams: list[TeamDto]
    tournamentCode: str = Field(..., description="Tournament code used to generate the match. This field was "
                                                 "added to match-v5 in patch 11.13 on June 23rd, 2021.")


class MatchDto(BaseModel):
    metadata: MetadataDto
    info: InfoDto

