class AccountV1_Endpoints:
    AccountByPuuid: str = '/riot/account/v1/accounts/by-puuid/{puuid}'
    AccountByRiotId: str = '/riot/account/v1/accounts/by-riot-id/{userName}/{tagLine}'
    ActiveShardForPlayer: str = '/riot/account/v1/active-shards/by-game/{game}/by-puuid/{puuid}'

class ChampionMasteryV4_Endpoints:
    MasteryByPuuid: str = '/lol/champion-mastery/v4/champion-masteries/by-puuid/{puuid}'
    MasteryByPuuidAndChampionID: str = \
        '/lol/champion-mastery/v4/champion-masteries/by-puuid/{puuid}/by-champion/{championId}'
    TopMasteryByPuuid: str = '/lol/champion-mastery/v4/champion-masteries/by-puuid/{puuid}/top'
    MasteryScoreByPuuid: str = '/lol/champion-mastery/v4/scores/by-puuid/{puuid}'

class ChampionV3_Endpoints:
    ChampionRotation: str = '/lol/platform/v3/champion-rotations'


class LolChallengesV1_Endpoints:
    ChallengeConfigInfo: str = '/lol/challenges/v1/challenges/config'
    ChallengeConfigInfoByChallengeId: str = '/lol/challenges/v1/challenges/{challengeId}/config'
    PercentileLevel: str = '/lol/challenges/v1/challenges/percentiles'
    PercentileLevelByChallengeId: str = '/lol/challenges/v1/challenges/{challengeId}/percentiles'
    PlayerData: str = '/lol/challenges/v1/player-data/{puuid}'


class MatchV5_Endpoints:
    ListMatchesByPuuid: str = '/lol/match/v5/matches/by-puuid/{puuid}/ids'
    GetMatchById: str = '/lol/match/v5/matches/{matchId}'
    GetMatchTimelineById: str = '/lol/match/v5/matches/{matchId}/timeline'
