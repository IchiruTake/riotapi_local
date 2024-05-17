import logging
import time
import random
from functools import partial
from threading import Event, Thread
from typing import Any
from queue import Queue
import backoff
import requests
import signal
import atexit
from sqlmodel import SQLModel, create_engine, Session
from copy import deepcopy
from sqlalchemy.exc import SQLAlchemyError
import itertools
from src.backend.riotapi.middlewares.monitor_src.client.base import MonitorClientBase
from src.backend.riotapi.middlewares.monitor_src.client.base import GET_TIME_COUNTER


# ================================================================
SQLITE_DB: str = "riotapi_monitor.db"
SQLITE_PARAMS: dict[str, str] = {
    "timeout": "10",
    "uri": "true",
    "cache": "private",
    "check_same_thread": "true",
}
DEBUG: bool = True
TRANSACTION_BATCH_SIZE: int = 128
MAX_FAILED_TRANSACTION: int = 3


class SyncMonitorClient(MonitorClientBase):
    def __init__(self) -> None:
        super(SyncMonitorClient, self).__init__()
        self._thread: Thread | None = None
        self._stop_sync_loop: Event = Event()
        self._requests_data_queue: Queue[tuple[float, dict[str, Any]]] = Queue()

        # Save monitoring health of the server by using SQLite database
        self._monitor_sqlite_datapath: str = SQLITE_DB
        params = "&".join([f"{k}={v}" for k, v in SQLITE_PARAMS.items()])
        self._engine = create_engine(f"sqlite:///file:{self._monitor_sqlite_datapath}?{params}", echo=DEBUG)
        SQLModel.metadata.create_all(self._engine)

    def start_sync_loop(self) -> None:
        logging.info("Starting sync loop for monitor client")
        self._stop_sync_loop.clear()        # Force to be False
        if self._thread is None or not self._thread.is_alive():
            logging.info("A daemon thread is created to run the sync loop")
            self._thread = Thread(target=self._run_sync_loop, daemon=True)
            self._thread.start()

            # Execute at-exit callback to stop the sync loop
            logging.info("Registering at-exit callback to stop the sync loop")
            atexit.register(self.stop_sync_loop)
            signal.signal(signal.SIGINT, self.stop_sync_loop)
            signal.signal(signal.SIGTERM, self.stop_sync_loop)

    def _run_sync_loop(self) -> None:
        try:
            last_sync_time: float = 0.0
            while not self._stop_sync_loop.is_set():
                try:
                    diff_time: float = GET_TIME_COUNTER() - last_sync_time
                    if diff_time >= self.sync_interval:
                        logging.info("Proceeding data to the monitor server")
                        self._proceed_data()
                        # Update the last sync time
                        last_sync_time = GET_TIME_COUNTER()
                    else:
                        logging.info(f"Waiting for the next sync interval at {self.sync_interval - diff_time} seconds")

                    # Small random sleep to avoid sync loop to be too predictable
                    time.sleep(random.uniform(0.25, 0.75))
                except Exception as e:  # pragma: no cover
                    logging.exception(e)
        finally:
            logging.info("Proceeding last data to the monitor server before stopping the sync loop")
            self._proceed_data()

    def stop_sync_loop(self, *args) -> None:
        # Set *args to handle the signal arguments
        self._stop_sync_loop.set()
        if self._thread is not None:
            self._thread.join()
            self._thread = None

    def _proceed_data(self) -> None:
        self._requests_data_queue.put_nowait((GET_TIME_COUNTER(), self.export()))
        transaction_tables: list[str] = self.list_transaction_payload()
        placeholder = []

        # Iterate through the queue to process the data
        while not self._requests_data_queue.empty():
            payload_time, payload = self._requests_data_queue.get_nowait()
            payload_if_failed: bool = False
            for table in transaction_tables:
                transactions = payload.get(table, [])
                if not transactions:    # Skip if there is no transaction data to be added
                    continue
                failed_lst = []

                with Session(self._engine) as ss:
                    with ss.begin():
                        for batch in itertools.batched(transactions, TRANSACTION_BATCH_SIZE):
                            try:
                                ss.add_all(batch)
                            except SQLAlchemyError as e:
                                ss.rollback()
                                logging.exception(e, exc_info=True)
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
            logging.info(f"Proceeding the payload of transaction {transaction_id} in "
                         f"{next_payload_time - payload_time} seconds.")
            if not payload_if_failed:
                self._requests_data_queue.task_done()
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

        for item in placeholder:
            self._requests_data_queue.put_nowait(item)
