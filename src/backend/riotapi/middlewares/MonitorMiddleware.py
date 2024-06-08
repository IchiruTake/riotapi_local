import contextlib
import json
import logging
import re
from typing import Any, Callable

from asgiref.typing import ASGI3Application, ASGIReceiveCallable, ASGISendCallable, ASGISendEvent
from asgiref.typing import Scope as ASGI3Scope
from httpx import HTTPStatusError
from starlette.concurrency import iterate_in_threadpool
from starlette.datastructures import MutableHeaders
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import BaseRoute, Match, Router, Route
from starlette.schemas import EndpointInfo, SchemaGenerator
from starlette.status import HTTP_422_UNPROCESSABLE_ENTITY
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR
from starlette.testclient import TestClient
from starlette.types import ASGIApp
from starlette.types import Scope as StarletteScope
from starlette.types import Send, Receive, Message

from src.backend.riotapi.middlewares.LocalMiddleware import BaseMiddleware
from src.backend.riotapi.middlewares.monitor_src.client.AsyncClient import AsyncMonitorClient
from src.backend.riotapi.middlewares.monitor_src.client.SyncClient import SyncMonitorClient
from src.backend.riotapi.middlewares.monitor_src.client.base import GET_TIME_COUNTER
from src.utils.timer import GetDurationOfPerfCounterInMs


# =============================================================================
def _register_shutdown_handler(app: ASGIApp | Router, shutdown_handler: Callable[[], Any]) -> None:
    if isinstance(app, Router):
        app.add_event_handler("shutdown", shutdown_handler)
    elif hasattr(app, "_app"):
        _register_shutdown_handler(app.app, shutdown_handler)


def _list_routes(app: ASGIApp | Router) -> list[BaseRoute | Route]:
    if isinstance(app, Router):
        return app.routes
    elif hasattr(app, "_app"):
        return _list_routes(app.app)
    return []  # pragma: no cover


def _list_endpoints(app: ASGIApp | Router) -> list[EndpointInfo]:
    routes = _list_routes(app)
    schemas = SchemaGenerator({})
    return schemas.get_endpoints(routes)


def analyze_app(app: ASGIApp, openapi_url: str | None = None) -> dict[str, Any]:
    app_info: dict[str, Any] = {}
    if openapi_url and (openapi := _get_openapi(app, openapi_url)):
        app_info["openapi"] = openapi
    if endpoints := _list_endpoints(app):
        app_info["paths"] = [{"path": endpoint.path, "method": endpoint.http_method} for endpoint in endpoints]
    # app_info["versions"] = get_versions("fastapi", "starlette", app_version=None)
    app_info["client"] = "python:starlette"
    return app_info


def _get_openapi(app: ASGIApp, openapi_url: str) -> str | None:
    with contextlib.suppress(HTTPStatusError):
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get(openapi_url)
        response.raise_for_status()
        return response.text


# =============================================================================
class MonitorMiddleware(BaseMiddleware):
    def __init__(self, app: ASGIApp | ASGI3Application, unmonitored_paths: list[str] | None,
                 identify_consumer_callback: Callable[[Request], str | None] | None = None):
        self.unmonitored_paths: list[str] = unmonitored_paths or []
        self._unmonitored_paths_regex: list[tuple[str, re.Pattern]] = \
            [(path, re.compile(path)) for path in (unmonitored_paths or [])]
        self.app_info: dict = analyze_app(app)
        self.identify_consumer_callback = identify_consumer_callback
        self.client: SyncMonitorClient | AsyncMonitorClient = AsyncMonitorClient()
        self.client.start_sync_loop()
        if hasattr(self.client, "shutdown") and callable(self.client.shutdown):
            _register_shutdown_handler(app, self.client.shutdown)
        super().__init__(app, accept_scope=None)

    async def __call__(self, scope: StarletteScope | ASGI3Scope, receive: ASGIReceiveCallable | Receive,
                       send: ASGISendCallable | Send) -> None:
        if not (await super()._precheck(scope, receive, send)):
            await self._app(scope, receive, send)
            return None
        # Pre-construct response
        response_length: int | None = 0
        response_status_code: int = 200
        response_headers: dict | None = {}
        response_media_type: str | None = None
        response_body: bytes | None = b""
        arr = bytearray()

        async def _send(message: Message | ASGISendEvent) -> None:
            nonlocal response_length, response_status_code, response_headers, response_media_type
            if message["type"] == "http.response.start":
                response_status_code = message["status"]
                response_headers = MutableHeaders(scope=message)
                response_media_type = (response_headers.get("content-type", None) or
                                       response_headers.get("Content-Type", None))
                response_length = response_headers.get("content-length", 0) or response_headers.get("Content-Length", 0)
            elif message["type"] == "http.response.body":
                nonlocal response_body
                more_body: bool = message.get("more_body", False)
                if not more_body:
                    response_body = message.get("body", b"")
                else:
                    while more_body:
                        arr.extend(message.get("body", b""))
                        await send(message)
                        more_body = message.get("more_body", False)

            await send(message)

        request: Request = Request(scope)
        start_time = GET_TIME_COUNTER()

        try:
            await self._app(scope, receive, _send)
            if arr:
                response_body = bytes(arr)
            if response_length == 0:
                response_length = len(response_body)
                response_headers["Content-Length"] = str(response_length)

            response: Response = Response(content=response_body, status_code=response_status_code,
                                          headers=response_headers, media_type=response_media_type,
                                          background=None)

        except BaseException as e:
            await self.add_request(
                request=request,
                response=None,
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                response_time=GetDurationOfPerfCounterInMs(start_time),
                exception=e,
            )
            raise e from None
        else:
            await self.add_request(
                request=request,
                response=response,
                status_code=response.status_code,
                response_time=GetDurationOfPerfCounterInMs(start_time),
            )

    async def add_request(self, request: Request, response: Response | None, status_code: int,
                          response_time: float, exception: BaseException | None = None) -> None:
        # [1]: Get the path template, for example: /items/{item_id} instead of /items/123
        path_template, is_handled_path = self.get_path_template(request)
        if any(pth == path_template or patt.match(path_template) for pth, patt in self._unmonitored_paths_regex):
            # Bypass monitoring for unmonitored paths
            logging.debug(f"Skipping monitoring for path: {path_template}")
            return None

        # [2]: Accumulate the request/response data
        consumer = self.get_consumer(request)
        c = self.client.request_counter[0]
        request_size: int = request.headers.get("Content-Length", len(await request.body()))
        response_size: int = response.headers.get("Content-Length", 0) if response is not None else 0

        c.accumulate(consumer=consumer, method=request.method, path=path_template, status_code=status_code,
                     response_time_in_second=response_time, request_size=request_size, response_size=response_size)

        if (status_code == HTTP_422_UNPROCESSABLE_ENTITY and response is not None and
                response.headers.get("Content-Type") == "application/json"):
            body = await self.get_response_json(response)
            # Log FastAPI / Pydantic validation errors
            c = self.client.validation_error_counter[0]
            c.accumulate(consumer=consumer, method=request.method, path=path_template, detail=body["detail"])

        if status_code == HTTP_500_INTERNAL_SERVER_ERROR and exception is not None:
            # Log server errors
            c = self.client.server_error_counter[0]
            c.accumulate(consumer=consumer, method=request.method, path=path_template, exception=exception)

    @staticmethod
    async def get_response_json(response: Response) -> Any:
        if hasattr(response, "body"):
            try:
                return json.loads(response.body)
            except json.JSONDecodeError:  # pragma: no cover
                return None
        elif hasattr(response, "body_iterator"): # StreamResponse
            try:
                response_body = [section async for section in response.body_iterator]
                response.body_iterator = iterate_in_threadpool(iter(response_body))
                return json.loads(b"".join(response_body))
            except json.JSONDecodeError:  # pragma: no cover
                return None

    @staticmethod
    def get_path_template(request: Request) -> tuple[str, bool]:
        for route in request.app.routes:
            match, _ = route.matches(request.scope)
            if match == Match.FULL:
                return route.path, True
        return request.url.path, False

    def get_consumer(self, request: Request) -> str | None:
        if hasattr(request.state, "consumer_identifier"):
            return str(request.state.consumer_identifier)
        if self.identify_consumer_callback is not None:
            consumer_identifier = self.identify_consumer_callback(request)
            if consumer_identifier is not None:
                return str(consumer_identifier)
        return None
