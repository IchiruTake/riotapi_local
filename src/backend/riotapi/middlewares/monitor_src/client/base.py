import itertools
import logging
import time
from asyncio import Queue as AsyncQueue
from copy import deepcopy
from datetime import datetime
from queue import Queue as SyncQueue
from typing import Any
from typing import Callable
from uuid import uuid4

from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Field, SQLModel, create_engine, Session

from src.static.static import (SYNC_INTERVAL, INITIAL_SYNC_INTERVAL, INITIAL_SYNC_INTERVAL_DURATION, SQLITE_DB,
                               SQLITE_PARAMS, TRANSACTION_BATCH_SIZE, MAX_FAILED_TRANSACTION)
from src.backend.riotapi.middlewares.monitor_src.healthcheck.request_counter import RequestCounter, RequestInfo, \
    RequestAnalysis
from src.backend.riotapi.middlewares.monitor_src.healthcheck.server_counter import ServerErrorCounter, ServerError
from src.backend.riotapi.middlewares.monitor_src.healthcheck.validation_counter import ValidationErrorCounter, \
    ValidationError
from src.log.timezone import GetProgramTimezone

# ========================================================
# Timer Triggering
GET_TIME_COUNTER: Callable = time.perf_counter

# Monitor Server Health - Configuration
DEBUG: bool = True


# ========================================================
class RequestInfoTransaction(SQLModel, table=True):
    id_counter: int | None = Field(default=None, primary_key=True)
    transaction_uuid: str = Field(index=True)
    export_time: str
    count: int = Field(gt=0)

    # Request Data
    request_data_consumer: str | None
    request_data_method: str = Field(index=True)
    request_data_path: str = Field(index=True)
    request_data_status_code: int = Field(index=True)

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
    d_counter: int | None = Field(default=None, primary_key=True)
    transaction_uuid: str = Field(index=True)
    export_time: str
    count: int
    error_data_consumer: str | None
    error_data_method: str
    error_data_path: str = Field(index=True)
    error_data_msg: str
    error_data_type: str


class ServerErrorTransaction(SQLModel, table=True):
    id_counter: int | None = Field(default=None, primary_key=True)
    transaction_uuid: str = Field(index=True)
    export_time: str
    count: int
    error_data_method: str
    error_data_path: str = Field(index=True)
    error_data_type: str
    error_data_msg: str
    error_data_traceback: str


class BaseMonitorClient:

    def __init__(self, queue: SyncQueue | AsyncQueue) -> None:
        super(BaseMonitorClient, self).__init__()

        # Self-enabled
        self.instance_id: str = str(uuid4())
        self.request_counter: tuple[RequestCounter, str] = \
            (RequestCounter(binTimeMode=True, binDataMode=False), "_requests")
        self.validation_error_counter: tuple[ValidationErrorCounter, str] = \
            (ValidationErrorCounter(), "_validation_errors")
        self.server_error_counter: tuple[ServerErrorCounter, str] = \
            (ServerErrorCounter(), "_server_errors")

        # Save monitoring health of the server by using SQLite database
        self._queue: SyncQueue | AsyncQueue = queue
        self._monitor_sqlite_datapath: str = SQLITE_DB
        params = "&".join([f"{k}={v}" for k, v in SQLITE_PARAMS.items()])
        self._engine = create_engine(f"sqlite:///file:{self._monitor_sqlite_datapath}?{params}", echo=DEBUG)
        SQLModel.metadata.create_all(self._engine)

        self._start_time: float = GET_TIME_COUNTER()

    def create_message(self) -> dict[str, Any]:
        return {"instance_id": self.instance_id, "transaction_uuid": str(uuid4())}

    def list_transaction_payload(self) -> list[str]:
        return [self.request_counter[1], self.validation_error_counter[1], self.server_error_counter[1]]

    @property
    def sync_interval(self) -> float:
        diff_time: float = GET_TIME_COUNTER() - self._start_time
        return SYNC_INTERVAL if diff_time > INITIAL_SYNC_INTERVAL_DURATION else INITIAL_SYNC_INTERVAL

    def _export(self) -> dict[str, Any]:
        logging.info("Monitoring data are exporting.")
        current_time = datetime.now(tz=GetProgramTimezone()).strftime("%Y%m%d %H%M%S")
        payload = self.create_message()

        transaction_uuid: str = payload["transaction_uuid"]

        # Requests
        payload[self.request_counter[1]] = []
        _requests: list[dict] = self.request_counter[0].export()
        for rq in _requests:
            _data: RequestInfo = rq["_data"]
            rp_time: RequestAnalysis = rq["response_time_analysis"]
            rq_size: RequestAnalysis = rq["request_size_analysis"]
            rp_size: RequestAnalysis = rq["response_size_analysis"]

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

    def proceed_data(self) -> None:
        logging.info("Pushing data to the monitor server")
        self._queue.put_nowait((GET_TIME_COUNTER(), self._export()))
        transaction_tables: list[str] = self.list_transaction_payload()
        placeholder = []

        # Iterate through the queue to process the data
        while not self._queue.empty():
            payload_time, payload = self._queue.get_nowait()
            payload_if_failed: bool = False
            for table in transaction_tables:
                transactions = payload.get(table, [])
                if not transactions:  # Skip if there is no transaction data to be added
                    continue
                failed_lst = []

                with Session(self._engine) as ss:
                    with ss.begin():
                        for batch in itertools.batched(transactions, TRANSACTION_BATCH_SIZE):
                            try:
                                ss.add_all(batch)
                            except SQLAlchemyError as e:
                                ss.rollback()
                                logging.exception(e)
                                failed_lst.extend(deepcopy(batch))
                                payload_if_failed = True
                            else:
                                ss.commit()
                if not failed_lst:
                    del payload[table]
                else:
                    payload[table] = failed_lst

            # If no failed transactions, then proceed to the next payload; otherwise, add back to the queue
            transaction_id: str = payload["transaction_uuid"]
            next_payload_time = GET_TIME_COUNTER()
            logging.info(f"Proceeding the transaction payload {transaction_id} in "
                         f"{1e3 * (next_payload_time - payload_time):.2f} milli-seconds.")
            if not payload_if_failed:
                self._queue.task_done()
                continue

            # Add back to the queue if there is any failed transactions
            failed_count: int = payload.get("failed_count", 0) + 1
            payload["failed_count"] = failed_count

            logging.warning(f"Failed to insert the payload {failed_count} time(s) into the monitoring database "
                            f"at transaction {transaction_id}")
            if failed_count > MAX_FAILED_TRANSACTION:
                logging.error(f"Exceeding the number of retry for this transaction {transaction_id}. Drop the payload.")
            else:
                placeholder.append((next_payload_time, payload))

        # Place back the failed transactions
        for item in placeholder:
            self._queue.put_nowait(item)

        return None
