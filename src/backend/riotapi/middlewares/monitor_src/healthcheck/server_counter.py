import textwrap
import traceback
from collections import Counter
from dataclasses import dataclass, asdict
from typing import Any, Optional

from src.backend.riotapi.middlewares.monitor_src.healthcheck.counter import BaseCounter

MAX_EXCEPTION_MSG_LENGTH: int = 2048
EXCEPTION_SUFFIX: str = "... (truncated)"
MAX_EXCEPTION_TRACEBACK_LENGTH: int = 65536
TRACEBACK_PREFIX: str = "... (truncated) ...\n"


@dataclass(slots=True, frozen=True)
class ServerError:
    consumer: Optional[str]
    method: str
    path: str
    type: str
    msg: str
    traceback: str


class ServerErrorCounter(BaseCounter):
    def __init__(self) -> None:
        super(ServerErrorCounter, self).__init__()
        self.error_counts: Counter[ServerError] = Counter()

    def accumulate(self, consumer: Optional[str], method: str, path: str, exception: BaseException) -> None:
        if not isinstance(exception, BaseException):
            return  # pragma: no cover
        exception_type = type(exception)
        with self.getLock():
            server_error = ServerError(
                consumer=consumer,
                method=method.upper(),
                path=path,
                type=f"{exception_type.__module__}.{exception_type.__qualname__}",
                msg=textwrap.fill(text=str(exception).strip(), width=MAX_EXCEPTION_MSG_LENGTH,
                                  placeholder=EXCEPTION_SUFFIX),
                traceback=self._get_truncated_exception_traceback(exception),
            )
            self.error_counts[server_error] += 1

    def export(self) -> list[dict[str, Any]]:
        data: list[dict[str, Any]] = []
        with self.getLock():
            for server_error, count in self.error_counts.items():
                server_error_asdict = asdict(server_error)
                if "_count" in server_error_asdict or "_data" in server_error_asdict:
                    raise ValueError("Cannot have '_count' or '_data' in server_error")
                server_error_asdict["_count"] = count
                server_error_asdict["_data"] = server_error
                data.append(server_error_asdict)

            self.error_counts.clear()
        return data

    @staticmethod
    def _get_truncated_exception_traceback(exception: BaseException) -> str:
        cutoff = MAX_EXCEPTION_TRACEBACK_LENGTH - len(TRACEBACK_PREFIX)
        lines = []
        length = 0
        for line in traceback.format_exception(exception)[::-1]:
            if length + len(line) > cutoff:
                lines.append(TRACEBACK_PREFIX)
                break
            lines.append(line)
            length += len(line)
        return "".join(lines[::-1]).strip()
