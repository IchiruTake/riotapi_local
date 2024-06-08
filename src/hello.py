import json
from src.backend.riotapi.routes.MatchV5 import MatchDto

with open('./src/mastery.json', 'r') as file:
    data = json.load(file)
    match = MatchDto(**data)
    print(match)