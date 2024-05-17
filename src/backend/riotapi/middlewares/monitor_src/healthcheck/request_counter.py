import logging
import numpy as np
import contextlib
from collections import Counter
from dataclasses import dataclass, asdict
from functools import lru_cache
from math import floor
from typing import Any

from src.backend.riotapi.middlewares.monitor_src.healthcheck.counter import BaseCounter

MAX_ITEMS_COUNT_FOR_ANALYSIS: int = 2048  # Maximum number of **value** to store in the counter
DIVISOR_UNIT: int = 1024  # 1KiB = 1024 bytes (kilobytes)
BIN_DATA_COLUMN: int = 128  # 128 bytes bin size
BIN_TIME_COLUMN: int = 10
BIN_TIME_UNIT: str = "ms"  # milliseconds --> Ensure the change is reflected in the TIME_UNIT_DIVISOR() function


@lru_cache(maxsize=1)
def TIME_UNIT_DIVISOR() -> int:
    UNIT_LIST = ["s", "ms", "us", "ns"]
    return 1000 ** UNIT_LIST.index(BIN_TIME_UNIT)


@dataclass(slots=True, frozen=True)
class RequestAnalysis:
    count: int
    full_total: int | float

    analysed_count: int
    average: int
    medium: int
    std: int
    p25: int
    p75: int
    p95: int
    p99: int


@dataclass(slots=True, frozen=True)
class RequestInfo:
    consumer: str | None
    method: str
    path: str
    status_code: int


class RequestCounter(BaseCounter):
    def __init__(self, binTimeMode: bool = True, binDataMode: bool = False) -> None:
        super(RequestCounter, self).__init__()
        self._binTimeMode: bool = binTimeMode
        self._binDataMode: bool = binDataMode
        self.request_counts: Counter[RequestInfo] = Counter()
        self.response_times: dict[RequestInfo, list[int]] = {}

        self.request_sizes: dict[RequestInfo, list[int]] = {}
        self.response_sizes: dict[RequestInfo, list[int]] = {}

    def accumulate(self, consumer: str | None, method: str, path: str, status_code: int,
                   response_time_in_second: float,
                   request_size: str | int | float | None = None,
                   response_size: str | int | float | None = None) -> None:
        def _castToBin(size: str | int | float, divisor: int, binMode: bool) -> int:
            size_as_bytes = size
            if isinstance(size, str):
                size_as_bytes: int = int(size)
            if not binMode:
                return size_as_bytes
            return int(floor(size_as_bytes / divisor) * divisor)

        response_time_as_bin: int = _castToBin(response_time_in_second * TIME_UNIT_DIVISOR(), BIN_TIME_COLUMN,
                                               binMode=self._binTimeMode)
        request_info = RequestInfo(consumer=consumer, method=method.upper(), path=path, status_code=status_code)
        with self.getLock():
            self.request_counts[request_info] += 1
            self.response_times.setdefault(request_info, []).append(response_time_as_bin)
            if request_size is not None:
                with contextlib.suppress(ValueError):
                    request_size_as_bin: int = _castToBin(int(request_size), BIN_DATA_COLUMN,
                                                          binMode=self._binDataMode)
                    self.request_sizes.setdefault(request_info, []).append(request_size_as_bin)

            if response_size is not None:
                with contextlib.suppress(ValueError):
                    response_size_as_bin: int = _castToBin(int(response_size), BIN_DATA_COLUMN,
                                                           binMode=self._binDataMode)
                    self.response_sizes.setdefault(request_info, []).append(response_size_as_bin)

    def export(self) -> list[dict[str, Any]]:
        data: list[dict[str, Any]] = []
        with self.getLock():
            for request_info, count in self.request_counts.items():
                request_info_asdict = asdict(request_info)
                if "_count" in request_info_asdict or "_data" in request_info_asdict:
                    raise ValueError("Cannot have '_count' or '_data' in request_info")
                request_info_asdict["_count"] = count
                request_info_asdict["_data"] = request_info
                request_info_asdict["response_times"] = self.response_times[request_info] or []
                request_info_asdict["request_sizes"] = self.request_sizes[request_info] or []
                request_info_asdict["response_sizes"] = self.response_sizes[request_info] or []

                request_info_asdict["response_time_analysis"] = RequestCounter._analyze(self.response_times[request_info])
                request_info_asdict["request_size_analysis"] = RequestCounter._analyze(self.request_sizes[request_info])
                request_info_asdict["response_size_analysis"] = RequestCounter._analyze(self.response_sizes[request_info])

                data.append(request_info_asdict)

            self.request_counts.clear()
            self.response_times.clear()
            self.request_sizes.clear()
            self.response_sizes.clear()
        return data

    @staticmethod
    def _analyze(lst: list[int | float]) -> RequestAnalysis:
        if len(lst) <= MAX_ITEMS_COUNT_FOR_ANALYSIS:
            analysed_lst = lst
        else:
            logging.debug(f"Too many items to analyse: {len(lst)}, which may cause high latency so only analysing "
                          f"first {MAX_ITEMS_COUNT_FOR_ANALYSIS} items.")
            analysed_lst = (lst[:MAX_ITEMS_COUNT_FOR_ANALYSIS]).copy()
        analysed_lst.sort()
        analysed_arr: np.ndarray = np.array(analysed_lst, dtype=np.float64)
        return RequestAnalysis(
            count=analysed_arr.size,
            full_total=sum(lst),
            analysed_count=len(lst),
            average=int(analysed_arr.mean()),
            medium=int(np.median(analysed_arr)),
            std=int(analysed_arr.std()),
            p25=int(np.percentile(analysed_arr, 25)),
            p75=int(np.percentile(analysed_arr, 75)),
            p95=int(np.percentile(analysed_arr, 95)),
            p99=int(np.percentile(analysed_arr, 99))
        )
