"""Utilities for parsing and executing structured command blocks emitted by the model."""
from __future__ import annotations

import json
from typing import Any, Callable, Dict, List, Optional, Tuple

from app import symbol_store
from app.types import Symbol


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
            # Stubs for unimplemented actions
            "query_symbols": self._handle_stub,
            "recurse_graph": self._handle_stub,
            "emit_feedback": self._handle_stub,
            "dispatch_task": self._handle_stub,
        }

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

        return commands

    def execute_commands(self, commands: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute a list of parsed command payloads."""

        results: List[Dict[str, Any]] = []
        for payload in commands:
            action = payload.get("action")
            if not action:
                results.append({"error": "missing_action", "payload": payload})
                continue

            handler = self._handlers.get(action, self._handle_unknown)
            result = handler(payload)
            results.append({"action": action, "result": result})

        return results

    def run(self, text: str) -> List[Dict[str, Any]]:
        """Convenience helper to parse and immediately execute commands."""

        commands = self.parse_commands(text)
        if not commands:
            return []
        return self.execute_commands(commands)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _extract_json_object(self, text: str, start_index: int) -> Tuple[Optional[str], int]:
        depth = 0
        in_string = False
        escape = False
        end_index = start_index

        for index in range(start_index, len(text)):
            char = text[index]
            end_index = index

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
        return updated

    def _handle_delete_symbol(self, payload: Dict[str, Any]):
        symbol_id = payload.get("symbol_id") or payload.get("id")
        if not symbol_id:
            return {"status": "error", "reason": "missing_symbol_id"}
        removed = symbol_store.delete_symbol(symbol_id)
        return {"status": "deleted" if removed else "not_found", "id": symbol_id}

    def _handle_load_symbol(self, payload: Dict[str, Any]):
        ids = payload.get("ids")
        if ids is None and payload.get("id"):
            ids = [payload["id"]]
        if not isinstance(ids, list):
            return []
        symbols = [symbol_store.get_symbol(symbol_id) for symbol_id in ids]
        return [symbol for symbol in symbols if symbol]

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
        return resolved

    def _handle_invoke_agent(self, payload: Dict[str, Any]):
        agent_id = payload.get("agent_id") or payload.get("id")
        if not agent_id:
            return {"status": "error", "reason": "missing_agent_id"}
        agent = symbol_store.get_agent(agent_id)
        if not agent:
            return {"status": "not_found", "agent_id": agent_id}
        return agent

    def _handle_stub(self, payload: Dict[str, Any]):
        return {"status": "not_implemented"}

    def _handle_unknown(self, payload: Dict[str, Any]):
        return {"status": "unknown_action", "payload": payload}


__all__ = ["CommandInterpreter"]
