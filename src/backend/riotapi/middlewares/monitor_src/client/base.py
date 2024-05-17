import logging
import time
from datetime import datetime
from src.log.timezone import GetProgramTimezone
from typing import Any, Callable
from uuid import uuid4
from sqlmodel import Field, SQLModel

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
class RequestInfoTransaction(SQLModel, table=True):
    transaction_uuid: str = Field(index=True)
    export_time: str
    count: int = Field(gt=0)

    # Request Data
    request_data_consumer: str | None
    request_data_method: str
    request_data_path: str = Field(index=True)
    request_data_status_code: int

    # Response Time
    response_time_full_total: int
    response_time_analysed_count: int
    response_time_average: int
    response_time_medium: int
    response_time_std: int
    response_time_p25: int
    response_time_p75: int
    response_time_p95: int
    response_time_p99: int

    # Request Size
    request_size_full_total: int
    request_size_analysed_count: int
    request_size_average: int
    request_size_medium: int
    request_size_std: int
    request_size_p25: int
    request_size_p75: int
    request_size_p95: int
    request_size_p99: int

    # Response Size
    response_size_full_total: int
    response_size_analysed_count: int
    response_size_average: int
    response_size_medium: int
    response_size_std: int
    response_size_p25: int
    response_size_p75: int
    response_size_p95: int
    response_size_p99: int


class ValidationErrorTransaction(SQLModel, table=True):
    transaction_uuid: str
    export_time: str
    count: int
    error_data_consumer: str | None
    error_data_method: str
    error_data_path: str
    error_data_msg: str
    error_data_type: str


class ServerErrorTransaction(SQLModel, table=True):
    transaction_uuid: str
    export_time: str
    count: int
    error_data_method: str
    error_data_path: str
    error_data_type: str
    error_data_msg: str
    error_data_traceback: str


class MonitorClientBase:

    def __init__(self) -> None:
        super(MonitorClientBase, self).__init__()

        # Self-enabled
        self.instance_id: str = str(uuid4())
        self.request_counter: tuple[RequestCounter, str] = \
            (RequestCounter(binTimeMode=True, binDataMode=False), "_requests")
        self.validation_error_counter: tuple[ValidationErrorCounter, str] = \
            (ValidationErrorCounter(), "_validation_errors")
        self.server_error_counter: tuple[ServerErrorCounter, str] = \
            (ServerErrorCounter(), "_server_errors")

        self._app_info_payload: dict[str, Any] | None = None
        self._app_info_sent: bool = False
        self._start_time: float = GET_TIME_COUNTER()

    def create_message(self) -> dict[str, Any]:
        return {"instance_id": self.instance_id, "transaction_uuid": str(uuid4())}

    def list_transaction_payload(self) -> list[str]:
        return [self.request_counter[1], self.validation_error_counter[1], self.server_error_counter[1] ]

    @property
    def sync_interval(self) -> float:
        diff_time: float = GET_TIME_COUNTER() - self._start_time
        return SYNC_INTERVAL if diff_time > INITIAL_SYNC_INTERVAL_DURATION else INITIAL_SYNC_INTERVAL

    def export(self) -> dict[str, Any]:
        logging.info("Monitoring data are exporting.")
        current_time = datetime.now(tz=GetProgramTimezone()).strftime("%Y%m%d %H%M%S")
        payload = self.create_message()

        transaction_uuid: str = payload["transaction_uuid"]

        # Requests
        payload[self.request_counter[1]] = []
        _requests: list[dict] = self.request_counter[0].export()
        for rq in _requests:
            _data: RequestInfo = rq["_data"]
            rp_time: RequestAnalysis = rq["response_times_analysis"]
            rq_size: RequestAnalysis = rq["request_sizes_analysis"]
            rp_size: RequestAnalysis = rq["response_sizes_analysis"]

            item = RequestInfoTransaction(
                transaction_uuid=transaction_uuid, export_time=current_time, count=rq["_count"],
                request_data_consumer=_data.consumer, request_data_method=_data.method,
                request_data_path=_data.path, request_data_status_code=_data.status_code,

                response_time_full_total=rp_time.full_total, response_time_analysed_count=rp_time.analysed_count,
                response_time_average=rp_time.average, response_time_medium=rp_time.medium,
                response_time_std=rp_time.std, response_time_p25=rp_time.p25, response_time_p75=rp_time.p75,
                response_time_p95=rp_time.p95, response_time_p99=rp_time.p99,

                request_size_full_total=rq_size.full_total, request_size_analysed_count=rq_size.analysed_count,
                request_size_average=rq_size.average, request_size_medium=rq_size.medium,
                request_size_std=rq_size.std, request_size_p25=rq_size.p25, request_size_p75=rq_size.p75,
                request_size_p95=rq_size.p95, request_size_p99=rq_size.p99,

                response_size_full_total=rp_size.full_total, response_size_analysed_count=rp_size.analysed_count,
                response_size_average=rp_size.average, response_size_medium=rp_size.medium,
                response_size_std=rp_size.std, response_size_p25=rp_size.p25, response_size_p75=rp_size.p75,
                response_size_p95=rp_size.p95, response_size_p99=rp_size.p99
            )
            payload[self.request_counter[1]].append(item)

        # Validation Errors
        payload[self.validation_error_counter[1]] = []
        _validation_errors = self.validation_error_counter[0].export()
        for ve in _validation_errors:
            _ve: ValidationError = ve["_data"]
            transaction = ValidationErrorTransaction(
                transaction_uuid=transaction_uuid,
                export_time=current_time,
                count=ve["_count"],
                error_data_consumer=_ve.consumer,
                error_data_method=_ve.method,
                error_data_path=_ve.path,
                error_data_msg=_ve.msg,
                error_data_type=_ve.type
            )
            payload[self.validation_error_counter[1]].append(transaction)

        # Server Errors
        payload[self.server_error_counter[1]] = []
        _server_errors = self.server_error_counter[0].export()
        for se in _server_errors:
            _se: ServerError = se["_data"]
            transaction = ServerErrorTransaction(
                transaction_uuid=transaction_uuid,
                export_time=current_time,
                count=se["_count"],
                error_data_method=_se.method,
                error_data_path=_se.path,
                error_data_type=_se.type,
                error_data_msg=_se.msg,
                error_data_traceback=_se.traceback
            )
            payload[self.server_error_counter[1]].append(transaction)

        return payload
