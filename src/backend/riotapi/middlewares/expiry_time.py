from datetime import datetime
from typing import Callable

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware


class ExpiryTimeMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, deadline: datetime | Callable):
        super().__init__(app)
        self.deadline: datetime | Callable = deadline

    async def dispatch(self, request: Request, call_next):
        # Check how many requests has been processed
        deadline: datetime = self.deadline if isinstance(self.deadline, datetime) else self.deadline()
        NOW = datetime.now(tz=deadline.tzinfo)
        if NOW > deadline:
            raise HTTPException(status_code=403, detail="Token expired or constraint setup by the programmer.")
        return await call_next(request)
