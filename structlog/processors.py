"""Processor implementations for the structlog shim."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict


def add_log_level(
    logger: Any, method_name: str, event_dict: Dict[str, Any]
) -> Dict[str, Any]:
    event_dict.setdefault("level", method_name)
    return event_dict


class TimeStamper:
    def __init__(self, fmt: str = "iso", utc: bool = False) -> None:
        self.fmt = fmt
        self.utc = utc

    def __call__(
        self, logger: Any, method_name: str, event_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        now = datetime.now(timezone.utc if self.utc else None)
        if self.fmt == "iso":
            stamp = now.isoformat()
        else:
            stamp = now.strftime(self.fmt)
        event_dict.setdefault("timestamp", stamp)
        return event_dict


class StackInfoRenderer:
    def __call__(
        self, logger: Any, method_name: str, event_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        stack = event_dict.pop("stack_info", None)
        if stack:
            event_dict["stack"] = stack
        return event_dict


def format_exc_info(
    logger: Any, method_name: str, event_dict: Dict[str, Any]
) -> Dict[str, Any]:
    exc_info = event_dict.pop("exc_info", None)
    if not exc_info:
        return event_dict

    if isinstance(exc_info, tuple):
        import traceback

        event_dict["exception"] = "".join(traceback.format_exception(*exc_info))
    else:
        event_dict["exception"] = str(exc_info)
    return event_dict


class JSONRenderer:
    def __call__(
        self, logger: Any, method_name: str, event_dict: Dict[str, Any]
    ) -> str:
        return json.dumps(event_dict, default=str)


__all__ = [
    "add_log_level",
    "TimeStamper",
    "StackInfoRenderer",
    "format_exc_info",
    "JSONRenderer",
]

