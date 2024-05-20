import atexit
import logging
import random
import signal
import time
from queue import Queue
from threading import Event, Thread

from src.backend.riotapi.middlewares.monitor_src.client.base import BaseMonitorClient
from src.backend.riotapi.middlewares.monitor_src.client.base import GET_TIME_COUNTER


class SyncMonitorClient(BaseMonitorClient):
    def __init__(self, ) -> None:
        super(SyncMonitorClient, self).__init__(queue=Queue())
        self._thread: Thread | None = None
        self._stop_sync_loop: Event = Event()

    def start_sync_loop(self) -> None:
        logging.info("Starting sync loop for monitor client")
        self._stop_sync_loop.clear()  # Force to be False
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
                        logging.info("Pushing data to the monitor server")
                        self.proceed_data()
                        # Update the last sync time
                        last_sync_time = GET_TIME_COUNTER()
                    else:
                        logging.info(f"Waiting for the next sync interval at {self.sync_interval - diff_time:.2f} "
                                     f"seconds")

                    # Small random sleep to avoid sync loop to be too predictable
                    time.sleep(random.uniform(0.25, 0.75))
                except Exception as e:  # pragma: no cover
                    logging.exception(e)
        finally:
            logging.info("Pushing last data to the monitor server before stopping the sync loop")
            self.proceed_data()

    def stop_sync_loop(self, *args) -> None:
        # Set *args to handle the signal arguments
        self._stop_sync_loop.set()
        if self._thread is not None:
            self._thread.join()
            self._thread = None
