import asyncio
import atexit
import logging
import signal
from math import ceil
from typing import Any

from src.backend.riotapi.middlewares.monitor_src.client.base import BaseMonitorClient
from src.backend.riotapi.middlewares.monitor_src.client.base import GET_TIME_COUNTER


class AsyncMonitorClient(BaseMonitorClient):
    def __init__(self) -> None:
        super(AsyncMonitorClient, self).__init__(queue=asyncio.Queue())
        self._stop_sync_loop = False
        self._sync_loop_task: asyncio.Task[Any] | None = None

    def start_sync_loop(self) -> None:
        self._stop_sync_loop = False
        self._sync_loop_task = asyncio.create_task(self._run_sync_loop())

        # Execute at-exit callback to stop the sync loop
        logging.info("Registering at-exit callback to stop the sync loop")
        atexit.register(self.stop_sync_loop)
        signal.signal(signal.SIGINT, self.stop_sync_loop)
        signal.signal(signal.SIGTERM, self.stop_sync_loop)

    async def _run_sync_loop(self) -> None:
        while not self._stop_sync_loop:
            try:
                time_start: float = GET_TIME_COUNTER()
                self.proceed_data()
                next_stop: int = max(0, ceil(self.sync_interval - (GET_TIME_COUNTER() - time_start)))
                if next_stop > 0:
                    logging.info(f"Sleeping for {next_stop} seconds before proceeding next data payload "
                                 f"to monitor server")
                    await asyncio.sleep(next_stop)
            except Exception as e:  # pragma: no cover
                logging.exception(e)

    def stop_sync_loop(self, *args) -> None:
        self._stop_sync_loop = True

    async def shutdown(self) -> None:
        if self._sync_loop_task is not None:
            self._sync_loop_task.cancel()
        # Send any remaining requests data before exiting
        logging.info("Proceeding last data to the monitor server before stopping the sync loop")
        self.proceed_data()
