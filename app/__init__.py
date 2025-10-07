"""Application package initialisation."""

from app.logging_config import configure_logging

configure_logging()

__all__ = ["configure_logging"]

