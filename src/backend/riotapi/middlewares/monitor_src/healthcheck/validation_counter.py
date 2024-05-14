from collections import Counter
from dataclasses import dataclass, asdict
from typing import Any, Tuple

from src.backend.riotapi.middlewares.monitor_src.healthcheck.counter import BaseCounter


@dataclass(slots=True, frozen=True)
class ValidationError:
    consumer: str | None
    method: str
    path: str
    loc: Tuple[str, ...]
    msg: str
    type: str


class ValidationErrorCounter(BaseCounter):
    def __init__(self) -> None:
        super(ValidationErrorCounter, self).__init__()
        self.error_counts: Counter[ValidationError] = Counter()

    def accumulate(self, consumer: str | None, method: str, path: str, detail: list[dict[str, Any]]) -> None:
        with self.getLock():
            for error in detail:
                try:
                    validation_error = ValidationError(
                        consumer=consumer,
                        method=method.upper(),
                        path=path,
                        loc=tuple(str(loc) for loc in error["loc"]),
                        msg=error["msg"],
                        type=error["type"],
                    )
                    self.error_counts[validation_error] += 1
                except (KeyError, TypeError):  # pragma: no cover
                    pass

    def export(self) -> list[dict[str, Any]]:
        data: list[dict[str, Any]] = []
        with self.getLock():
            for validation_error, count in self.error_counts.items():
                validation_error_asdict = asdict(validation_error)
                if "_count" in validation_error_asdict or "_data" in validation_error_asdict:
                    raise ValueError("Cannot have '_count' in validation_error")
                validation_error_asdict["_count"] = count
                validation_error_asdict["_data"] = validation_error
                data.append(validation_error_asdict)

            self.error_counts.clear()
        return data
