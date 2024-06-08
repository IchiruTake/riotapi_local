import logging
from math import ceil
from time import perf_counter
from typing import Callable, Any
from src.static.static import MINUTE, YEAR
from datetime import datetime
from starlette.types import ASGIApp
from starlette.types import Scope as StarletteScope
from starlette.exceptions import HTTPException
from starlette.status import HTTP_429_TOO_MANY_REQUESTS, HTTP_403_FORBIDDEN
from asgiref.typing import Scope as ASGI3Scope
from starlette.types import Send, Receive, Message
from asgiref.typing import ASGI3Application, ASGIReceiveCallable, ASGISendCallable, ASGISendEvent
from starlette.datastructures import MutableHeaders

# ==============================================================================
# Rate Limiting
class BaseMiddleware:
    def __init__(self, application: ASGIApp | ASGI3Application, accept_scope: str | list[str] | None = "http"):
        self._app: ASGIApp | ASGI3Application = application
        accept_scope = list(set(accept_scope)) if isinstance(accept_scope, list) else accept_scope
        _accept = ["http", "websocket", "lifespan"]
        msg: str = f"Invalid scope: {accept_scope}. Must be one or part of {', '.join(_accept)}, or None."
        if isinstance(accept_scope, str):
            if accept_scope not in _accept:
                logging.critical(msg)
                raise ValueError(msg)
        elif isinstance(accept_scope, list):
            for scope in accept_scope:
                if scope not in _accept:
                    logging.critical(msg)
                    raise ValueError(msg)
        elif accept_scope is not None:
            logging.critical(msg)
            raise ValueError(msg)
        self._scope: str | list[str] = accept_scope

    async def _precheck(self, scope: StarletteScope | ASGI3Scope, receive: ASGIReceiveCallable | Receive,
                        send: ASGISendCallable | Send) -> bool:
        if isinstance(self._scope, str):
            if scope["type"] != self._scope:
                return False
        elif isinstance(self._scope, list):
            if scope["type"] not in self._scope:
                return False
        return True

    async def __call__(self, scope: StarletteScope | ASGI3Scope, receive: ASGIReceiveCallable | Receive,
                       send: ASGISendCallable | Send) -> None:
        raise NotImplementedError("You must implement this method in your subclass.")

# ==============================================================================
# Rate Limiting
class RateLimitMiddleware(BaseMiddleware):
    def __init__(self, app: ASGIApp | ASGI3Application, max_requests: int, interval_by_second: int = MINUTE,
                 time_operator: Callable[[], int | float] = perf_counter, accept_scope: str | list[str] = "http"):
        super(RateLimitMiddleware, self).__init__(app, accept_scope=accept_scope)
        self.max_requests: int = max_requests
        self.interval_by_second: int = interval_by_second
        self._operator: Callable = time_operator
        self._num_processed_requests: int = 0
        self._last_request_time: float = self._operator()

    async def __call__(self, scope: StarletteScope | ASGI3Scope, receive: ASGIReceiveCallable | Receive,
                       send: ASGISendCallable | Send) -> None:
        if not (await super()._precheck(scope, receive, send)):
            await self._app(scope, receive, send)
            return None

        # Check how many requests has been processed
        current_time = self._operator()
        diff_time: float = current_time - self._last_request_time
        current_processed_requests = ceil(self.max_requests * diff_time) // self.interval_by_second
        self._num_processed_requests = max(0, self._num_processed_requests - current_processed_requests) + 1
        self._last_request_time = current_time

        # Rate Limiting Decision
        if self._num_processed_requests > self.max_requests:
            remaining_requests = self._num_processed_requests - self.max_requests
            est_time = remaining_requests * self.interval_by_second / self.max_requests
            message = (f"Rate limit exceeded ({remaining_requests} requests remaining). "
                       f"Try again in {est_time:.2f} seconds.")
            raise HTTPException(status_code=HTTP_429_TOO_MANY_REQUESTS, detail=message)

        # OK to process the request
        await self._app(scope, receive, send)


# ==============================================================================
# Expiry Date
class ExpiryDateMiddleware(BaseMiddleware):
    def __init__(self, app: ASGIApp | ASGI3Application, deadline: datetime | Callable[[], datetime],
                 accept_scope: str | list[str] = "http"):
        super(ExpiryDateMiddleware, self).__init__(app, accept_scope=accept_scope)
        self._deadline: datetime | Callable[[], datetime] = deadline

    async def __call__(self, scope: StarletteScope | ASGI3Scope, receive: ASGIReceiveCallable | Receive,
                       send: ASGISendCallable | Send) -> None:
        if not (await super()._precheck(scope, receive, send)):
            await self._app(scope, receive, send)
            return None

        # Check if our application would be expired to stop all traffic
        deadline: datetime = self._deadline if isinstance(self._deadline, datetime) else self._deadline()
        if datetime.now(tz=deadline.tzinfo) > deadline:
            raise HTTPException(status_code=HTTP_403_FORBIDDEN,
                                detail="Token expired or constraint setup by the programmer.")
        await self._app(scope, receive, send)

# ==============================================================================
# Header Hardening
class HeaderHardeningMiddleware(BaseMiddleware):
    def __init__(self, app: ASGIApp | ASGI3Application, accept_scope: str | list[str] = "http"):
        super(HeaderHardeningMiddleware, self).__init__(app, accept_scope=accept_scope)
        # Offload the headers
        # https://scotthelme.co.uk/hardening-your-http-response-headers
        # https://faun.pub/hardening-the-http-security-headers-with-aws-lambda-edge-and-cloudfront-2e2da1ae4d83
        # https://scotthelme.co.uk/content-security-policy-an-introduction/
        # https://scotthelme.co.uk/a-new-security-header-feature-policy/?ref=scotthelme.co.uk
        # https://scotthelme.co.uk/content-security-policy-an-introduction/

        self._headers: dict[str, Any] = {
            "Strict-Transport-Security": f"max-age={YEAR}; includeSubDomains",
            # "Public-Key-Pins": "pin-sha256='X3pGTSOuJeEVw989IJ/cEtXUEmy52zs1TZQrU06KUKg='; "
            #                    "pin-sha256='MHJYVThihUrJcxW6wcqyOISTXIsInsdj3xK8QrZbHec='; "
            #                    "pin-sha256='isi41AizREkLvvft0IRW4u3XMFR2Yg7bvrF7padyCJg='; "
            #                    "includeSubdomains; max-age=2592000"
            "X-Frame-Options": "SAMEORIGIN",
            "X-Content-Type-Options": "nosniff",
            "X-XSS-Protection": '1; mode=block',
            "Content-Security-Policy": ';'.join(["default-src 'self'", "upgrade-insecure-requests",
                                                 'report-to "http://localhost:8081/csp-report"']),
            "Referrer-Policy": "no-referrer-when-downgrade",
            "Feature-Policy": "geolocation none; midi none; notifications none; push none; sync-xhr none; "
                              "microphone none; camera none; magnetometer none; gyroscope none; speaker self; "
                              "vibrate none; fullscreen self; payment none;",
            "Access-Control-Expose-Headers": ','.join(["X-Request-Timestamp", "X-Response-Timestamp",
                                                       "X-Response-DurationInMilliseconds", "Content-Length",
                                                       "Content-Type", "Transfer-Encoding", "Content-Encoding",]),
        }

    async def __call__(self, scope: StarletteScope | ASGI3Scope, receive: ASGIReceiveCallable | Receive,
                       send: ASGISendCallable | Send) -> None:
        if not (await super()._precheck(scope, receive, send)):
            await self._app(scope, receive, send)
            return None

        # Add the headers
        async def _send_with_headers(message: Message | ASGISendEvent) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                for key, value in self._headers.items():
                    headers.append(key, value)
            await send(message)

        await self._app(scope, receive, _send_with_headers)

