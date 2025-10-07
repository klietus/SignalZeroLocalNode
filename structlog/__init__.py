"""Minimal structlog-compatible shim for environments without the dependency."""
from __future__ import annotations

import logging
from typing import Any, Iterable, Optional

from . import contextvars, processors, stdlib

_processors: list[Any] = []
_wrapper_class: Optional[type] = None
_logger_factory: Optional[Any] = None
_cache: dict[Optional[str], Any] = {}
_cache_enabled = False


def configure(
    *,
    processors: Iterable[Any],
    wrapper_class: type,
    logger_factory: Any,
    cache_logger_on_first_use: bool = False,
) -> None:
    """Store configuration for subsequent :func:`get_logger` calls."""

    global _processors, _wrapper_class, _logger_factory, _cache_enabled, _cache

    _processors = list(processors)
    _wrapper_class = wrapper_class
    _logger_factory = logger_factory
    _cache_enabled = cache_logger_on_first_use
    if not cache_logger_on_first_use:
        _cache = {}


def get_logger(name: Optional[str] = None) -> Any:
    """Return a configured logger wrapper."""

    global _cache

    if _cache_enabled and name in _cache:
        return _cache[name]

    factory = _logger_factory or stdlib.LoggerFactory()
    logger = factory(name)
    if logger is None:
        logger = logging.getLogger(name)

    wrapper_cls = _wrapper_class or stdlib.BoundLogger
    wrapped = wrapper_cls(logger, list(_processors), {})

    if _cache_enabled:
        _cache[name] = wrapped

    return wrapped


__all__ = [
    "configure",
    "get_logger",
    "contextvars",
    "processors",
    "stdlib",
]

