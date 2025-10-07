"""Helpers for integrating command execution results into conversational context."""
from __future__ import annotations

import json
from typing import Dict, Iterable, List

import structlog

from app.logging_config import configure_logging
from app.symbol_store import get_symbol
from app.types import Symbol


configure_logging()
log = structlog.get_logger(__name__)


def _collect_symbols_from_result(result: object) -> List[Symbol]:
    collected: List[Symbol] = []

    if isinstance(result, Symbol):
        collected.append(result)
    elif isinstance(result, list):
        for item in result:
            collected.extend(_collect_symbols_from_result(item))
    elif isinstance(result, dict):
        for value in result.values():
            collected.extend(_collect_symbols_from_result(value))

    return collected


def _stringify(value: object) -> str:
    def _serialize(obj: object) -> object:
        if isinstance(obj, Symbol):
            return obj.model_dump()
        if isinstance(obj, list):
            return [_serialize(item) for item in obj]
        if isinstance(obj, dict):
            return {key: _serialize(val) for key, val in obj.items()}
        return obj

    try:
        return json.dumps(_serialize(value), sort_keys=True)
    except TypeError:
        return repr(value)


def _add_symbols_to_context(
    symbols: Iterable[Symbol],
    context_symbols: List[Symbol],
    symbol_lookup: Dict[str, Symbol],
) -> List[str]:
    added_ids: List[str] = []

    for symbol in symbols:
        if not isinstance(symbol, Symbol):
            continue
        if symbol.id in symbol_lookup:
            continue
        context_symbols.append(symbol)
        symbol_lookup[symbol.id] = symbol
        added_ids.append(symbol.id)

    if added_ids:
        log.info("command_utils.symbols_added", count=len(added_ids))

    return added_ids


def _load_linked_symbols(
    context_symbols: List[Symbol],
    symbol_lookup: Dict[str, Symbol],
) -> List[str]:
    added_ids: List[str] = []

    for symbol in list(context_symbols):
        linked_ids = getattr(symbol, "lnk", None)
        if not isinstance(linked_ids, list):
            continue
        for linked_id in linked_ids:
            if not isinstance(linked_id, str):
                continue
            if linked_id in symbol_lookup:
                continue
            linked_symbol = get_symbol(linked_id)
            if linked_symbol is None:
                log.debug("command_utils.linked_symbol_missing", symbol_id=linked_id)
                continue
            context_symbols.append(linked_symbol)
            symbol_lookup[linked_symbol.id] = linked_symbol
            added_ids.append(linked_symbol.id)

    return added_ids


def integrate_command_results(
    commands: List[Dict[str, object]],
    context_symbols: List[Symbol],
    symbol_lookup: Dict[str, Symbol],
) -> List[str]:
    """Apply command side-effects and return summary strings for history."""

    history_notes: List[str] = []

    for entry in commands:
        action = entry.get("action") if isinstance(entry, dict) else None
        result = entry.get("result") if isinstance(entry, dict) else None

        if action in {"load_symbol", "load_kit"}:
            symbols = _collect_symbols_from_result(result)
            added = _add_symbols_to_context(symbols, context_symbols, symbol_lookup)
            if added:
                note = f"{action}: added symbols {added}"
                history_notes.append(note)
            else:
                note = f"{action}: no new symbols added"
                history_notes.append(note)
            log.info(
                "command_utils.command_processed",
                action=action,
                added=len(added),
            )
        elif action == "recurse_graph":
            added = _load_linked_symbols(context_symbols, symbol_lookup)
            if added:
                note = f"recurse_graph: loaded linked symbols {added}"
                history_notes.append(note)
            else:
                note = "recurse_graph: no linked symbols loaded"
                history_notes.append(note)
            log.info("command_utils.recurse_graph", added=len(added))
        else:
            note = f"{action}: {_stringify(result)}"
            history_notes.append(note)
            log.debug(
                "command_utils.command_logged",
                action=action,
                has_result=result is not None,
            )

    log.debug("command_utils.integration_complete", notes=len(history_notes))
    return history_notes


__all__ = ["integrate_command_results"]
