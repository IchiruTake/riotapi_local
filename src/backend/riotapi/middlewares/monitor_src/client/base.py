import os
import re
from functools import cached_property

import time
from typing import Any, Optional, Type, TypeVar, cast, Callable
from uuid import UUID, uuid4

from src.backend.riotapi.middlewares.monitor_src.healthcheck.counter import BaseCounter
from src.backend.riotapi.middlewares.monitor_src.healthcheck.request_counter import RequestCounter
from src.backend.riotapi.middlewares.monitor_src.healthcheck.validation_counter import ValidationErrorCounter
from src.backend.riotapi.middlewares.monitor_src.healthcheck.server_counter import ServerErrorCounter


HUB_BASE_URL = os.getenv("APITALLY_HUB_BASE_URL") or "https://hub.apitally.io"
HUB_VERSION = "v1"
REQUEST_TIMEOUT = 10
MAX_QUEUE_TIME = 3600
SYNC_INTERVAL = 60
INITIAL_SYNC_INTERVAL = 10
INITIAL_SYNC_INTERVAL_DURATION = 3600

TApitallyClient = TypeVar("TApitallyClient", bound="ApitallyClientBase")

GET_TIME_COUNTER: Callable = time.perf_counter


class MonitorClientBase(BaseCounter):

    def __init__(self, client_id: str, env: str) -> None:
        super(MonitorClientBase, self).__init__()
        try:
            UUID(client_id)
        except ValueError:
            raise ValueError(f"invalid client_id '{client_id}' (expecting hexadecimal UUID format)")
        if re.match(r"^[\w-]{1,32}$", env) is None:
            raise ValueError(f"invalid env '{env}' (expecting 1-32 alphanumeric lowercase characters and hyphens only)")

        # Self-enabled
        self.client_id: str = client_id
        self.env: str = env
        self.instance_uuid: str = str(uuid4())
        self.request_counter = RequestCounter()
        self.validation_error_counter = ValidationErrorCounter()
        self.server_error_counter = ServerErrorCounter()

        self._app_info_payload: dict[str, Any] | None = None
        self._app_info_sent: bool = False
        self._start_time: float = GET_TIME_COUNTER()

    def create_message(self) -> dict[str, Any]:
        return {"instance_uuid": self.instance_uuid, "message_uuid": str(uuid4())}

    @property
    def sync_interval(self) -> float:
        diff_time: float = GET_TIME_COUNTER() - self._start_time
        return SYNC_INTERVAL if diff_time > INITIAL_SYNC_INTERVAL_DURATION else INITIAL_SYNC_INTERVAL

    @cached_property
    def hub_url(self) -> str:
        return f"{HUB_BASE_URL}/{HUB_VERSION}/{self.client_id}/{self.env}"

    def get_info_payload(self, app_info: dict[str, Any]) -> dict[str, Any]:
        payload = self.create_message()
        payload.update(app_info)
        return payload

    def export(self) -> dict[str, Any]:
        payload = self.create_message()
        payload["requests"] = self.request_counter.export()
        payload["validation_errors"] = self.validation_error_counter.export()
        payload["server_errors"] = self.server_error_counter.export()
        return payload
