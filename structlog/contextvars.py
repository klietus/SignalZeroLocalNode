"""Simplified contextvars helpers for the structlog shim."""
from __future__ import annotations

from typing import Any, Dict


def merge_contextvars(
    logger: Any, method_name: str, event_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """No-op merge implementation.

    The real structlog implementation integrates with context variables. For
    the purposes of the shim we simply return the original event dictionary.
    """

    return event_dict


__all__ = ["merge_contextvars"]

