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

class ClashV1_Endpoints:
    GetBySummonerId: str = "/lol/clash/v1/players/by-summoner/{summonerId}"
    GetByTeamId: str = "/lol/clash/v1/teams/{teamId}"
    GetTournaments: str = "/lol/clash/v1/tournaments"
    GetTournamentByTeamId: str = "/lol/clash/v1/tournaments/by-team/{teamId}"
    GetTournamentByTournamentId: str = "/lol/clash/v1/tournaments/{tournamentId}"

class LeagueExpV4_Endpoints:
    GetLeagueEntries: str = '/lol/league-exp/v4/entries/{queue}/{tier}/{division}'

class LeagueV4_Endpoints:
    GetChallengerLeague: str = '/lol/league/v4/challengerleagues/by-queue/{queue}'
    GetGrandmasterLeague: str = '/lol/league/v4/grandmasterleagues/by-queue/{queue}'
    GetMasterLeague: str = '/lol/league/v4/masterleagues/by-queue/{queue}'

    GetLeagueEntriesBySummonerID: str = '/lol/league/v4/entries/by-summoner/{encryptedSummonerId}'
    GetLeagueEntries: str = '/lol/league/v4/entries/{queue}/{tier}/{division}'

    # Consistently looking up league ids that don't exist will result in a blacklist.
    GetLeagueEntriesByLeagueID: str = '/lol/league/v4/leagues/{leagueId}'
