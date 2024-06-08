from fastapi.routing import APIRouter
from src.backend.riotapi.inapp import DefaultSettings

class CustomAPIRouter(APIRouter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.inapp_default: DefaultSettings | None = None
