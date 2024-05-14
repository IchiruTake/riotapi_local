import logging
import time
from dataclasses import dataclass
from typing import Any, TypeVar, Callable
from uuid import UUID, uuid4

from src.backend.riotapi.middlewares.monitor_src.healthcheck.counter import BaseCounter
from src.backend.riotapi.middlewares.monitor_src.healthcheck.request_counter import RequestCounter, RequestInfo, \
    RequestAnalysis
from src.backend.riotapi.middlewares.monitor_src.healthcheck.validation_counter import ValidationErrorCounter, \
    ValidationError
from src.backend.riotapi.middlewares.monitor_src.healthcheck.server_counter import ServerErrorCounter, ServerError

# ========================================================
REQUEST_TIMEOUT = 10
MAX_QUEUE_TIME = 3600
SYNC_INTERVAL = 60  # 1 minute
INITIAL_SYNC_INTERVAL = 10  # Force to have quick data response
INITIAL_SYNC_INTERVAL_DURATION = 600  # 10 minutes

GET_TIME_COUNTER: Callable = time.perf_counter


# ========================================================
@dataclass(slots=True, frozen=True)
class RequestInfoTransaction:
    transaction_uuid: str
    _count: int
    request_data: RequestInfo
    response_times: RequestAnalysis
    request_sizes: RequestAnalysis
    response_sizes: RequestAnalysis


@dataclass(slots=True, frozen=True)
class ValidationErrorTransaction:
    transaction_uuid: str
    _count: int
    error_data: ValidationError


@dataclass(slots=True, frozen=True)
class ServerErrorTransaction:
    transaction_uuid: str
    _count: int
    error_data: ServerError


class MonitorClientBase(BaseCounter):

    def __init__(self) -> None:
        super(MonitorClientBase, self).__init__()

        # Self-enabled
        self.instance_id: str = str(uuid4())
        self.request_counter = RequestCounter()
        self.validation_error_counter = ValidationErrorCounter()
        self.server_error_counter = ServerErrorCounter()

        self._app_info_payload: dict[str, Any] | None = None
        self._app_info_sent: bool = False
        self._start_time: float = GET_TIME_COUNTER()

    def create_message(self) -> dict[str, Any]:
        return {"instance_id": self.instance_id, "transaction_uuid": str(uuid4())}

    @property
    def sync_interval(self) -> float:
        diff_time: float = GET_TIME_COUNTER() - self._start_time
        return SYNC_INTERVAL if diff_time > INITIAL_SYNC_INTERVAL_DURATION else INITIAL_SYNC_INTERVAL

    def export(self) -> dict[str, Any]:
        logging.info("Monitoring data has been exported.")
        payload = self.create_message()
        transaction_uuid: str = payload["transaction_uuid"]
        # Requests
        payload["_requests"] = []
        _requests: list[dict] = self.request_counter.export()
        for rq in _requests:
            item = RequestInfoTransaction(transaction_uuid=transaction_uuid, _count=rq["_count"],
                                          request_data=rq["_data"], response_times=rq["response_times_analysis"],
                                          request_sizes=rq["request_sizes_analysis"],
                                          response_sizes=rq["response_sizes_analysis"])
            payload["_requests"].append(item)

        # Validation Errors
        payload["_validation_errors"] = []
        _validation_errors = self.validation_error_counter.export()
        for ve in _validation_errors:
            transaction = ValidationErrorTransaction(transaction_uuid=transaction_uuid, _count=ve["_count"],
                                                     error_data=ve["_data"])
            payload["_validation_errors"].append(transaction)

        # Server Errors
        payload["_server_errors"] = []
        _server_errors = self.server_error_counter.export()
        for se in _server_errors:
            transaction = ServerErrorTransaction(transaction_uuid=transaction_uuid, _count=se["_count"],
                                                 error_data=se["_data"])
            payload["_server_errors"].append(transaction)

        return payload
