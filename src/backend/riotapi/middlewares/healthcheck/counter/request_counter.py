from __future__ import annotations

import contextlib
from collections import Counter
from dataclasses import dataclass, asdict
from functools import lru_cache
from math import floor
from typing import Any, Dict, Optional

from src.backend.riotapi.middlewares.healthcheck.counter.counter import BaseCounter

DIVISOR_UNIT: int = 1024  # 1KiB = 1024 bytes (kilobytes)
BIN_DATA_COLUMN: int = 128  # 128 bytes bin size
BIN_TIME_COLUMN: int = 10
BIN_TIME_UNIT: str = "ms"  # milliseconds --> Ensure the change is reflected in the TIME_UNIT_DIVISOR() function


@lru_cache(maxsize=1)
def TIME_UNIT_DIVISOR() -> int:
    UNIT_LIST = ["s", "ms", "us", "ns"]
    return 1000 ** UNIT_LIST.index(BIN_TIME_UNIT)


@dataclass(slots=True, frozen=True)
class RequestInfo:
    consumer: str | None
    method: str
    path: str
    status_code: int


class RequestCounter(BaseCounter):
    def __init__(self) -> None:
        super(RequestCounter, self).__init__()
        self.request_counts: Counter[RequestInfo] = Counter()
        self.response_times: Dict[RequestInfo, Counter[int]] = {}

        self.request_size_sums: Counter[RequestInfo] = Counter()
        self.response_size_sums: Counter[RequestInfo] = Counter()
        self.request_sizes: Dict[RequestInfo, Counter[int]] = {}
        self.response_sizes: Dict[RequestInfo, Counter[int]] = {}

    def accumulate(self, consumer: str | None, method: str, path: str, status_code: int, response_time_in_second: float,
                   request_size: Optional[str | int | float] = None, response_size: Optional[str | int] = None) -> None:
        response_time_as_bin: int = int(floor(response_time_in_second / BIN_TIME_COLUMN) * BIN_TIME_COLUMN)
        response_time_as_bin *= TIME_UNIT_DIVISOR()
        request_info = RequestInfo(consumer=consumer, method=method.upper(), path=path, status_code=status_code)
        with self.getLock():
            self.request_counts[request_info] += 1
            self.response_times.setdefault(request_info, Counter())[response_time_as_bin] += 1
            if request_size is not None:
                with contextlib.suppress(ValueError):
                    request_size_as_bytes: int = int(request_size)
                    request_size_as_bin: int = int(floor(request_size_as_bytes / BIN_DATA_COLUMN) * BIN_DATA_COLUMN)
                    self.request_size_sums[request_info] += request_size_as_bytes
                    self.request_sizes.setdefault(request_info, Counter())[request_size_as_bin] += 1

            if response_size is not None:
                with contextlib.suppress(ValueError):
                    response_size_as_bytes: int = int(response_size)
                    response_size_as_bin: int = int(floor(response_size_as_bytes / BIN_DATA_COLUMN) * BIN_DATA_COLUMN)
                    self.response_size_sums[request_info] += response_size_as_bytes
                    self.response_sizes.setdefault(request_info, Counter())[response_size_as_bin] += 1

    def export(self) -> list[dict[str, Any]]:
        data: list[dict[str, Any]] = []
        with self.getLock():
            for request_info, count in self.request_counts.items():
                request_info_asdict = asdict(request_info)
                if "_count" in request_info_asdict:
                    raise ValueError("Cannot have '_count' in request_info")
                request_info_asdict["_count"] = count
                request_info_asdict["request_size_sum"] = request_info_asdict["consumer"] or None
                request_info_asdict["response_size_sum"] = request_info_asdict["consumer"] or None
                request_info_asdict["response_times"] = request_info_asdict["consumer"] or None
                request_info_asdict["request_sizes"] = request_info_asdict["consumer"] or None
                request_info_asdict["response_sizes"] = request_info_asdict["consumer"] or None
                data.append(request_info_asdict)

            self.request_counts.clear()
            self.request_size_sums.clear()
            self.response_size_sums.clear()
            self.response_times.clear()
            self.request_sizes.clear()
            self.response_sizes.clear()
        return data
