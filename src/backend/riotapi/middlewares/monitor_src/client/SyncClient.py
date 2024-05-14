import logging
import time
from functools import partial
from threading import Event, Thread
from typing import Any, Callable
from queue import Queue
import backoff
import requests
import signal
import atexit
from src.backend.riotapi.middlewares.monitor_src.client.base import MonitorClientBase
from src.backend.riotapi.middlewares.monitor_src.client.base import MAX_QUEUE_TIME, REQUEST_TIMEOUT, GET_TIME_COUNTER

retry = partial(
    backoff.on_exception,
    backoff.expo,
    requests.RequestException,
    max_tries=3,
    logger=logging,
    giveup_log_level=logging.WARNING,
)


class SyncMonitorClient(MonitorClientBase):
    def __init__(self, monitor_datapath: str) -> None:
        super(SyncMonitorClient, self).__init__()
        self._thread: Thread | None = None
        self._stop_sync_loop: Event = Event()
        self._requests_data_queue: Queue[tuple[float, dict[str, Any]]] = Queue()

    def start_sync_loop(self) -> None:
        self._stop_sync_loop.clear()        # Force to be False
        if self._thread is None or not self._thread.is_alive():
            self._thread = Thread(target=self._run_sync_loop, daemon=True)
            self._thread.start()

            # Execute at-exit callback to stop the sync loop
            atexit.register(self.stop_sync_loop)
            signal.signal(signal.SIGINT, self.stop_sync_loop)
            signal.signal(signal.SIGTERM, self.stop_sync_loop)

    def _run_sync_loop(self) -> None:
        try:
            last_sync_time = 0.0
            while not self._stop_sync_loop.is_set():
                try:
                    now = GET_TIME_COUNTER()
                    if (now - last_sync_time) >= self.sync_interval:
                        with requests.Session() as session:
                            if not self._app_info_sent and last_sync_time > 0:  # not on first sync
                                self.send_app_info(session)
                            self.send_requests_data(session)
                        last_sync_time = now
                    time.sleep(1)
                except Exception as e:  # pragma: no cover
                    logging.exception(e)
        finally:
            # Send any remaining requests data before exiting
            with requests.Session() as session:
                self.send_requests_data(session)

    def stop_sync_loop(self, *args) -> None:
        # Set *args to handle the signal arguments
        self._stop_sync_loop.set()
        if self._thread is not None:
            self._thread.join()
            self._thread = None

    def set_app_info(self, app_info: dict[str, Any]) -> None:
        self._app_info_sent = False
        self._app_info_payload = self.get_info_payload(app_info)
        with requests.Session() as session:
            self.send_app_info(session)

    def send_app_info(self, session: requests.Session) -> None:
        if self._app_info_payload is not None:
            self._send_app_info(session, self._app_info_payload)

    def send_requests_data(self, session: requests.Session) -> None:
        payload = self.export()
        self._requests_data_queue.put_nowait((GET_TIME_COUNTER(), payload))

        failed_items = []
        while not self._requests_data_queue.empty():
            payload_time, payload = self._requests_data_queue.get_nowait()
            try:
                if (time_offset := GET_TIME_COUNTER() - payload_time) <= MAX_QUEUE_TIME:
                    payload["time_offset"] = time_offset
                    self._send_requests_data(session, payload)
                self._requests_data_queue.task_done()
            except requests.RequestException:
                failed_items.append((payload_time, payload))
        for item in failed_items:
            self._requests_data_queue.put_nowait(item)

    @retry(raise_on_giveup=False)
    def _send_app_info(self, session: requests.Session, payload: dict[str, Any]) -> None:
        logging.debug("Sending app info")
        response = session.post(url=f"{self.hub_url}/info", json=payload, timeout=REQUEST_TIMEOUT)
        if response.status_code == 404:
            self.stop_sync_loop()
            logging.error(f"Invalid Apitally client ID {self.client_id}")
        else:
            response.raise_for_status()
        self._app_info_sent = True
        self._app_info_payload = None

    @retry()
    def _send_requests_data(self, session: requests.Session, payload: dict[str, Any]) -> None:
        logging.debug("Sending requests data")
        response = session.post(url=f"{self.hub_url}/requests", json=payload, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
