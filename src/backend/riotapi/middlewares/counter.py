from math import ceil
from time import perf_counter
from typing import Callable
from src.utils.static import MINUTE
from datetime import datetime


# ==============================================================================
# Rate Limiting
class RateLimitCounter:
    def __init__(self, max_requests: int, interval_by_second: int = MINUTE,
                 time_operator: Callable[[], int | float] = perf_counter):
        self._operator: Callable = time_operator
        self.max_requests: int = max_requests
        self.interval_by_second: int = interval_by_second

        self._num_processed_requests: int = 0
        self._last_request_time: float = self._operator()

    def increment(self) -> tuple[bool, int | float]:
        # Check how many requests has been processed
        current_time = self._operator()
        diff_time: float = current_time - self._last_request_time
        current_processed_requests = ceil(self.max_requests * diff_time) // self.interval_by_second
        self._num_processed_requests = max(0, self._num_processed_requests - current_processed_requests) + 1
        self._last_request_time = current_time

        # Rate Limiting Decision
        if self._num_processed_requests > self.max_requests:
            remaining_requests = self._num_processed_requests - self.max_requests
            est_time = remaining_requests * self.interval_by_second / self.max_requests
            # message = (f"Rate limit exceeded ({remaining_requests} requests remaining). "
            #            f"Try again in {est_time:.2f} seconds.")
            # raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=message)
            return False, est_time

        # OK to process the request
        return True, 0

class ExpiryDateCounter:
    def __init__(self, deadline: datetime | Callable[[], datetime]):
        self._deadline: datetime | Callable[[], datetime] = deadline

    def is_ok(self) -> tuple[bool, str]:
        # Check if our application would be expired to stop all traffic
        deadline: datetime = self._deadline if isinstance(self._deadline, datetime) else self._deadline()
        if datetime.now(tz=deadline.tzinfo) > deadline:
            return False, f"Application is expired automatically or constraint setup by the programmer on {deadline}."
        return True, "OK"
