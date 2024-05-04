from pydantic import BaseModel, Field
from fastapi.routing import APIRouter

router = APIRouter()

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