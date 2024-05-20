import contextlib
import json
import logging
import re
from typing import Any, Callable

from httpx import HTTPStatusError
from starlette.concurrency import iterate_in_threadpool
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import BaseRoute, Match, Router
from starlette.schemas import EndpointInfo, SchemaGenerator
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR, HTTP_422_UNPROCESSABLE_ENTITY
from starlette.testclient import TestClient
from starlette.types import ASGIApp

from src.backend.riotapi.middlewares.common import get_versions
from src.backend.riotapi.middlewares.monitor_src.client.AsyncClient import AsyncMonitorClient
from src.backend.riotapi.middlewares.monitor_src.client.SyncClient import SyncMonitorClient
from src.backend.riotapi.middlewares.monitor_src.client.base import GET_TIME_COUNTER

__all__ = ["ApitallyMiddleware"]


# =============================================================================
def _register_shutdown_handler(app: ASGIApp | Router, shutdown_handler: Callable[[], Any]) -> None:
    if isinstance(app, Router):
        app.add_event_handler("shutdown", shutdown_handler)
    elif hasattr(app, "app"):
        _register_shutdown_handler(app.app, shutdown_handler)


def _list_routes(app: ASGIApp | Router) -> list[BaseRoute]:
    if isinstance(app, Router):
        return app.routes
    elif hasattr(app, "app"):
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
    app_info["versions"] = get_versions("fastapi", "starlette", app_version=None)
    app_info["client"] = "python:starlette"
    return app_info


def _get_openapi(app: ASGIApp, openapi_url: str) -> str | None:
    with contextlib.suppress(HTTPStatusError):
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get(openapi_url)
        response.raise_for_status()
        return response.text


# =============================================================================
class ApitallyMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, unmonitored_paths: list[str] | None,
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
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start_time = GET_TIME_COUNTER()
        try:
            response = await call_next(request)
        except BaseException as e:
            await self.add_request(
                request=request,
                response=None,
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                response_time=GET_TIME_COUNTER() - start_time,
                exception=e,
            )
            raise e from None
        else:
            await self.add_request(
                request=request,
                response=response,
                status_code=response.status_code,
                response_time=GET_TIME_COUNTER() - start_time,
            )
        return response

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
        c.accumulate(consumer=consumer, method=request.method, path=path_template, status_code=status_code,
                     response_time_in_second=response_time, request_size=request.headers.get("Content-Length", 0),
                     response_size=response.headers.get("Content-Length", 0) if response is not None else None)

        if (status_code == HTTP_422_UNPROCESSABLE_ENTITY and response is not None and
                response.headers.get("Content-Type") == "application/json"):
            body = await self.get_response_json(response)
            # Log FastAPI / Pydantic validation errors
            c = self.client.validation_error_counter[0]
            c.accumulate(consumer=consumer, method=request.method, path=path_template, detail=body["detail"])

        if status_code == 500 and exception is not None:
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
        elif hasattr(response, "body_iterator"):
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
