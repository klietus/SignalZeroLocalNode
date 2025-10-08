"""Configuration for default agents and symbols injected into prompts."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Sequence

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "data" / "default_context_config.json"


@lru_cache(maxsize=1)
def _load_config() -> dict:
    data = json.loads(_CONFIG_PATH.read_text())
    agents = data.get("default_agent_ids")
    symbols = data.get("default_symbol_ids")
    if not isinstance(agents, list) or not isinstance(symbols, list):
        raise ValueError("default context configuration is malformed")
    return {
        "default_agent_ids": tuple(str(a) for a in agents),
        "default_symbol_ids": tuple(str(s) for s in symbols),
    }


def get_default_agent_ids() -> Sequence[str]:
    """Return the configured default agent identifiers."""

    return _load_config()["default_agent_ids"]


def get_default_symbol_ids() -> Sequence[str]:
    """Return the configured default symbol identifiers."""

    return _load_config()["default_symbol_ids"]


DEFAULT_AGENT_IDS = get_default_agent_ids()
DEFAULT_SYMBOL_IDS = get_default_symbol_ids()
