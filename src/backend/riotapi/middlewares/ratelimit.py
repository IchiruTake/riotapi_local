from math import ceil
from time import perf_counter
from typing import Callable

from fastapi import FastAPI, Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from src.utils.static import MINUTE


# ==============================================================================
# Rate Limiting
def _time_measure() -> int | float:
    return perf_counter()


class RateLimiterMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: FastAPI, max_requests: int, interval_by_second: int = MINUTE,
                 time_operator: Callable = _time_measure):
        super().__init__(app)
        self._operator: Callable = time_operator
        self.max_requests: int = max_requests
        self.interval_by_second: int = interval_by_second

        self.num_processed_requests: int = 0
        self.last_request_time: float = self._operator()

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        # Check how many requests has been processed
        current_time = self._operator()
        diff_time: float = current_time - self.last_request_time
        current_processed_requests = ceil(self.max_requests * diff_time) // self.interval_by_second
        self.num_processed_requests = max(0, self.num_processed_requests - current_processed_requests) + 1
        self.last_request_time = current_time

        # Rate Limiting Decision
        if self.num_processed_requests > self.max_requests:
            remaining_requests = self.num_processed_requests - self.max_requests
            est_time = remaining_requests * self.interval_by_second / self.max_requests
            message = (f"Rate limit exceeded ({remaining_requests} requests remaining). "
                       f"Try again in {est_time:.2f} seconds.")
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=message)

        # Process the request
        return await call_next(request)
