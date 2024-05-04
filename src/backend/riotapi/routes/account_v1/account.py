import logging
from fastapi.routing import APIRouter

router = APIRouter()


def riotapi_region_routing(user_region: str) -> str:
    # For user account searching, any region is valid
    mapping = {
        "BR1": "AMERICAS",
        "EUN1": "EUROPE",
        "EUW1": "EUROPE",
        "JP1": "ASIA",
        "KR": "ASIA",
        "LA1": "AMERICAS",
        "LA2": "AMERICAS",
        "NA1": "AMERICAS",
        "OC1": "SEA",
        "PH2": "SEA",
        "RU": "EUROPE",
        "SG2": "SEA",
        "TH2": "SEA",
        "TR1": "EUROPE",
        "TW2": "SEA",
        "VN2": "SEA"
    }
    if user_region not in mapping:
        logging.error(f"Invalid region: {user_region}")
    return mapping[user_region]





@app.get("/")
async def get_riot_account():
    url = "https://asia.api.riotgames.com/riot/account/v1/accounts/by-riot-id/SlayerIchiruTake/5092"
    headers = {
        "X-Riot-Token": "YOUR_API_KEY"  # Replace with your Riot API key
    }
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
