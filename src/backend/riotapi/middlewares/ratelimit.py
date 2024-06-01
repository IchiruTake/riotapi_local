from fastapi import FastAPI, Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from src.backend.riotapi.middlewares.counter import RateLimitCounter, ExpiryDateCounter

# ==============================================================================

class RateLimiterMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: FastAPI, rate_limit_counters: list[RateLimitCounter],
                 expiry_date_counter: list[ExpiryDateCounter]):
        super().__init__(app)
        self._rate_limit_counters: list[RateLimitCounter] = rate_limit_counters or []
        self._expiry_date_counter: list[ExpiryDateCounter] = expiry_date_counter or []

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        # Check how many requests has been processed
        for rate_limit_counter in self._rate_limit_counters:
            is_ok, est_time = rate_limit_counter.increment()
            if not is_ok:
                message = f"Rate limit exceeded. Try again in {est_time:.2f} seconds."
                raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=message)

        # Check if our application would be expired to stop all traffic
        for expiry_date_counter in self._expiry_date_counter:
            is_ok, message = expiry_date_counter.is_ok()
            if not is_ok:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=message)

        # Process the request
        return await call_next(request)
