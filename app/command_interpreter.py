"""Utilities for parsing and executing structured command blocks emitted by the model."""
from __future__ import annotations

import json
from typing import Any, Callable, Dict, List, Optional, Tuple

import structlog

from app import symbol_store
from app.logging_config import configure_logging
from app.types import Symbol


configure_logging()
log = structlog.get_logger(__name__)


class CommandInterpreter:
    """Parse ⟐CMD blocks and dispatch supported actions."""

    _TOKEN = "⟐CMD"

    def __init__(self) -> None:
        self._handlers: Dict[str, Callable[[Dict[str, Any]], Any]] = {
            "store_symbol": self._handle_store_symbol,
            "update_symbol": self._handle_update_symbol,
            "delete_symbol": self._handle_delete_symbol,
            "load_symbol": self._handle_load_symbol,
            "load_kit": self._handle_load_kit,
            "invoke_agent": self._handle_invoke_agent,
            "query_symbols": self._handle_query_symbols,
            "recurse_graph": self._handle_recurse_graph,
            "emit_feedback": self._handle_stub,
            "dispatch_task": self._handle_stub,
        }
        log.debug("command_interpreter.initialised", handler_count=len(self._handlers))

    @property
    def handler_count(self) -> int:
        return len(self._handlers)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def parse_commands(self, text: str) -> List[Dict[str, Any]]:
        """Extract JSON payloads from ⟐CMD blocks in the provided text."""

        commands: List[Dict[str, Any]] = []
        search_start = 0

        while True:
            token_index = text.find(self._TOKEN, search_start)
            if token_index == -1:
                break

            brace_start = text.find("{", token_index)
            if brace_start == -1:
                break

            json_payload, search_start = self._extract_json_object(text, brace_start)
            if not json_payload:
                break

            try:
                payload = json.loads(json_payload)
            except json.JSONDecodeError:
                continue

            if isinstance(payload, dict):
                commands.append(payload)

        log.debug("command_interpreter.parsed", command_count=len(commands))
        return commands

    def execute_commands(self, commands: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute a list of parsed command payloads."""

        results: List[Dict[str, Any]] = []
        for payload in commands:
            action = payload.get("action")
            if not action:
                results.append({"error": "missing_action", "payload": payload})
                log.warning("command_interpreter.missing_action", payload=payload)
                continue

            handler = self._handlers.get(action, self._handle_unknown)
            try:
                result = handler(payload)
                log.info("command_interpreter.executed", action=action)
            except Exception as exc:  # pragma: no cover - defensive logging
                log.error(
                    "command_interpreter.execution_failed",
                    action=action,
                    error=str(exc),
                    payload=payload,
                )
                result = {"status": "error", "reason": str(exc)}
            results.append({"action": action, "result": result, "payload": payload})

        return results

    def run(self, text: str) -> List[Dict[str, Any]]:
        """Convenience helper to parse and immediately execute commands."""

        commands = self.parse_commands(text)
        if not commands:
            log.debug("command_interpreter.run_empty")
            return []
        return self.execute_commands(commands)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _extract_json_object(self, text: str, start_index: int) -> Tuple[Optional[str], int]:
        depth = 0
        in_string = False
        escape = False

        for index in range(start_index, len(text)):
            char = text[index]

            if in_string:
                if escape:
                    escape = False
                    continue
                if char == "\\":
                    escape = True
                    continue
                if char == '"':
                    in_string = False
                continue

            if char == '"':
                in_string = True
                continue

            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return text[start_index : index + 1], index + 1

        return None, len(text)

    # ------------------------------------------------------------------
    # Action handlers
    # ------------------------------------------------------------------
    def _handle_store_symbol(self, payload: Dict[str, Any]):
        symbol_data = payload.get("symbol")
        if not isinstance(symbol_data, dict) or "id" not in symbol_data:
            return {"status": "error", "reason": "invalid_symbol"}

        symbol = Symbol(**symbol_data)
        symbol_store.put_symbol(symbol.id, symbol)
        log.info("command_interpreter.store_symbol", symbol_id=symbol.id)
        return symbol

    def _handle_update_symbol(self, payload: Dict[str, Any]):
        symbol_data = payload.get("symbol")
        if not isinstance(symbol_data, dict) or "id" not in symbol_data:
            return {"status": "error", "reason": "invalid_symbol"}

        existing = symbol_store.get_symbol(symbol_data["id"])
        base = existing.model_dump() if existing else {}
        base.update(symbol_data)
        updated = Symbol(**base)
        symbol_store.put_symbol(updated.id, updated)
        log.info("command_interpreter.update_symbol", symbol_id=updated.id)
        return updated

    def _handle_delete_symbol(self, payload: Dict[str, Any]):
        symbol_id = payload.get("symbol_id") or payload.get("id")
        if not symbol_id:
            return {"status": "error", "reason": "missing_symbol_id"}
        removed = symbol_store.delete_symbol(symbol_id)
        log.info("command_interpreter.delete_symbol", symbol_id=symbol_id, removed=removed)
        return {"status": "deleted" if removed else "not_found", "id": symbol_id}

    def _handle_load_symbol(self, payload: Dict[str, Any]):
        ids = payload.get("ids")
        if ids is None and payload.get("id"):
            ids = [payload["id"]]
        if not isinstance(ids, list):
            return []
        symbols = [symbol_store.get_symbol(symbol_id) for symbol_id in ids]
        found = [symbol for symbol in symbols if symbol]
        log.info("command_interpreter.load_symbols", requested=len(ids), returned=len(found))
        return found

    def _handle_load_kit(self, payload: Dict[str, Any]):
        kit_id = payload.get("kit_id") or payload.get("kit")
        if not kit_id:
            return {"status": "error", "reason": "missing_kit_id"}
        kit = symbol_store.get_kit(kit_id)
        if not kit:
            return {"status": "not_found", "kit_id": kit_id}
        resolved = dict(kit)
        resolved["triad"] = [sym for sym in kit.get("triad", [])]
        resolved["exec"] = [sym for sym in kit.get("exec", [])]
        anchor = kit.get("anchor")
        if anchor is not None:
            resolved["anchor"] = anchor
        log.info("command_interpreter.load_kit", kit_id=kit_id)
        return resolved

    def _handle_invoke_agent(self, payload: Dict[str, Any]):
        agent_id = payload.get("agent_id") or payload.get("id")
        if not agent_id:
            return {"status": "error", "reason": "missing_agent_id"}
        agent = symbol_store.get_agent(agent_id)
        if not agent:
            return {"status": "not_found", "agent_id": agent_id}
        log.info("command_interpreter.invoke_agent", agent_id=agent_id)
        return agent

    def _handle_query_symbols(self, payload: Dict[str, Any]):
        ids = payload.get("ids")
        if isinstance(ids, list):
            symbols = symbol_store.get_symbols_by_ids(ids)
            log.info("command_interpreter.query_symbols", requested=len(ids), returned=len(symbols))
            return symbols
        return {"status": "unsupported_query"}

    def _handle_recurse_graph(self, payload: Dict[str, Any]):
        # The calling context is responsible for materialising linked symbols.
        depth = payload.get("depth")
        query = payload.get("query")
        log.debug("command_interpreter.recurse_graph", depth=depth, query=query)
        return {"status": "queued", "depth": depth, "query": query}

    def _handle_stub(self, payload: Dict[str, Any]):
        log.debug("command_interpreter.stub_called", payload=payload.get("action"))
        return {"status": "not_implemented"}

    def _handle_unknown(self, payload: Dict[str, Any]):
        log.warning("command_interpreter.unknown_action", payload=payload)
        return {"status": "unknown_action", "payload": payload}


__all__ = ["CommandInterpreter"]
