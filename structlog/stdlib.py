"""Stdlib helpers for the structlog shim."""
from __future__ import annotations

import logging
from typing import Any, Dict, Iterable, Optional


class LoggerFactory:
    """Return stdlib loggers."""

    def __call__(self, name: Optional[str] = None) -> logging.Logger:
        return logging.getLogger(name)


class BoundLogger:
    """Minimal bound logger compatible with structlog's API surface."""

    def __init__(
        self,
        logger: logging.Logger,
        processors: Iterable[Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        self._logger = logger
        self._processors = list(processors)
        self._context = dict(context or {})

    def bind(self, **new_context: Any) -> "BoundLogger":
        context = dict(self._context)
        context.update(new_context)
        return type(self)(self._logger, self._processors, context)

    def new(self, **new_context: Any) -> "BoundLogger":
        return type(self)(self._logger, self._processors, new_context)

    def _log(self, level: str, event: str, **event_dict: Any) -> None:
        data = dict(self._context)
        data.update(event_dict)
        data.setdefault("event", event)

        exc_info = data.pop("exc_info", None)

        for processor in self._processors:
            data = processor(self._logger, level, data)

        extra = {"structlog_event_dict": data}
        log_method = getattr(self._logger, level)
        log_method(data.get("event", event), extra=extra, exc_info=exc_info)

    def debug(self, event: str, **event_dict: Any) -> None:
        self._log("debug", event, **event_dict)

    def info(self, event: str, **event_dict: Any) -> None:
        self._log("info", event, **event_dict)

    def warning(self, event: str, **event_dict: Any) -> None:
        self._log("warning", event, **event_dict)

    def error(self, event: str, **event_dict: Any) -> None:
        self._log("error", event, **event_dict)

    def critical(self, event: str, **event_dict: Any) -> None:
        self._log("critical", event, **event_dict)

    def exception(self, event: str, **event_dict: Any) -> None:
        event_dict.setdefault("exc_info", True)
        self._log("error", event, **event_dict)


class ProcessorFormatter(logging.Formatter):
    """Apply structlog-style processors to stdlib log records."""

    def __init__(
        self,
        *,
        processor: Any,
        foreign_pre_chain: Optional[Iterable[Any]] = None,
    ) -> None:
        super().__init__()
        self.processor = processor
        self.foreign_pre_chain = list(foreign_pre_chain or [])

    def format(self, record: logging.LogRecord) -> str:
        event_dict = getattr(
            record,
            "structlog_event_dict",
            {"event": record.getMessage(), "level": record.levelname.lower()},
        )

        method_name = record.levelname.lower()
        for processor in self.foreign_pre_chain:
            event_dict = processor(None, method_name, dict(event_dict))

        rendered = self.processor(None, method_name, event_dict)
        if not isinstance(rendered, str):
            rendered = str(rendered)
        return rendered

    @staticmethod
    def wrap_for_formatter(
        logger: Any, method_name: str, event_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        return event_dict


__all__ = ["LoggerFactory", "BoundLogger", "ProcessorFormatter"]

