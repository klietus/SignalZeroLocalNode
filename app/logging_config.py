"""Central logging configuration using structlog with stdlib integration."""
from __future__ import annotations

import logging
import logging.config
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

import structlog


_CONFIGURED = False


def _ensure_log_directory() -> Path:
    base_dir = Path(__file__).resolve().parent.parent
    log_dir = base_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def _rotate_on_start(log_file: Path) -> None:
    if not log_file.exists():
        return

    timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
    rotated = log_file.with_name(f"{log_file.stem}.{timestamp}{log_file.suffix}")
    try:
        log_file.replace(rotated)
    except OSError:
        pass


def _build_logging_config(log_file: Path) -> Dict[str, Any]:
    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)

    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        timestamper,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "structlog": {
                "()": structlog.stdlib.ProcessorFormatter,
                "processor": structlog.processors.JSONRenderer(),
                "foreign_pre_chain": shared_processors,
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "structlog",
                "level": "INFO",
            },
            "file": {
                "class": "logging.handlers.TimedRotatingFileHandler",
                "formatter": "structlog",
                "level": "INFO",
                "filename": str(log_file),
                "when": "H",
                "interval": 1,
                "backupCount": 0,
                "encoding": "utf-8",
                "utc": True,
            },
        },
        "root": {
            "handlers": ["console", "file"],
            "level": "INFO",
        },
    }


def configure_logging() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    log_dir = _ensure_log_directory()
    log_file = log_dir / "app.log"
    _rotate_on_start(log_file)

    logging.config.dictConfig(_build_logging_config(log_file))

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    _CONFIGURED = True


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Return a configured structlog logger for the given module name."""

    configure_logging()
    return structlog.get_logger(name)


__all__ = ["configure_logging", "get_logger"]

