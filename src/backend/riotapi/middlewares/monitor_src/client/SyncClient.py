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

from sqlmodel import Field, SQLModel, create_engine, Session

from src.backend.riotapi.middlewares.monitor_src.client.base import MonitorClientBase
from src.backend.riotapi.middlewares.monitor_src.client.base import MAX_QUEUE_TIME, REQUEST_TIMEOUT, GET_TIME_COUNTER

retry = partial(
    backoff.on_exception,
    backoff.expo,
    requests.RequestException,
    max_tries=3,
    logger=logging,
    backoff_log_level=logging.INFO,
    giveup_log_level=logging.WARNING,
)


class SyncMonitorClient(MonitorClientBase):
    def __init__(self, monitor_datapath: str) -> None:
        super(SyncMonitorClient, self).__init__()
        self._thread: Thread | None = None
        self._stop_sync_loop: Event = Event()
        self._requests_data_queue: Queue[tuple[float, dict[str, Any]]] = Queue()

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
                    now = GET_TIME_COUNTER()
                    if (now - last_sync_time) >= self.sync_interval:
                        logging.info("Syncing data to monitor server")
                        with requests.Session() as session:
                            self.send_requests_data(session)

                        # Update the last sync time
                        last_sync_time = now

                    # Random sleep to avoid sync loop to be too predictable
                    time.sleep(random.uniform(0.25, 1.5))
                except Exception as e:  # pragma: no cover
                    logging.exception(e)
        finally:
            logging.info("Send any remaining requests data before exiting")
            with requests.Session() as session:
                self.send_requests_data(session)

    def stop_sync_loop(self, *args) -> None:
        # Set *args to handle the signal arguments
        self._stop_sync_loop.set()
        if self._thread is not None:
            self._thread.join()
            self._thread = None


    def _proceed_data(self) -> None:
        pass

    def send_requests_data(self, session: requests.Session) -> None:
        payload = self.export()
        self._requests_data_queue.put_nowait((GET_TIME_COUNTER(), payload))

        failed_items = []
        while not self._requests_data_queue.empty():
            payload_time, payload = self._requests_data_queue.get_nowait()
            try:
                if (time_offset := GET_TIME_COUNTER() - payload_time) <= MAX_QUEUE_TIME:
                    payload["time_offset"] = time_offset
                    # self._send_requests_data(session, payload)
                self._requests_data_queue.task_done()
            except requests.RequestException:
                failed_items.append((payload_time, payload))
        for item in failed_items:
            self._requests_data_queue.put_nowait(item)

