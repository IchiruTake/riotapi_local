from datetime import datetime
from typing import Callable

from fastapi import HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.status import HTTP_403_FORBIDDEN


class ExpiryTimeMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, deadline: datetime | Callable):
        super().__init__(app)
        self.deadline: datetime | Callable = deadline

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Check how many requests has been processed
        deadline: datetime = self.deadline if isinstance(self.deadline, datetime) else self.deadline()
        if datetime.now(tz=deadline.tzinfo) > deadline:
            raise HTTPException(status_code=HTTP_403_FORBIDDEN,
                                detail="Token expired or constraint setup by the programmer.")
        return await call_next(request)
