from types import SimpleNamespace

from app import command_interpreter
from app.command_interpreter import CommandInterpreter
from app.types import Symbol


def test_parse_and_execute(monkeypatch):
    stored_symbols = {}

    def fake_put(symbol_id, symbol):
        stored_symbols[symbol_id] = symbol

    def fake_get(symbol_id):
        return stored_symbols.get(symbol_id)

    def fake_delete(symbol_id):
        return bool(stored_symbols.pop(symbol_id, None))

    dummy_kit = {"kit": "kit-1", "triad": [Symbol(id="S1")], "exec": [], "anchor": None}

    monkeypatch.setattr(command_interpreter.symbol_store, "put_symbol", fake_put)
    monkeypatch.setattr(command_interpreter.symbol_store, "get_symbol", fake_get)
    monkeypatch.setattr(command_interpreter.symbol_store, "delete_symbol", fake_delete)
    monkeypatch.setattr(command_interpreter.symbol_store, "get_kit", lambda kit_id: dummy_kit)
    monkeypatch.setattr(
        command_interpreter.symbol_store,
        "get_agent",
        lambda agent_id: SimpleNamespace(id=agent_id, name="Agent"),
    )

    payload = """
    Thoughtful reply.
    ⟐CMD {"action": "store_symbol", "symbol": {"id": "S1", "macro": "macro"}}
    ⟐CMD {"action": "load_symbol", "ids": ["S1"]}
    ⟐CMD {"action": "load_kit", "kit": "kit-1"}
    ⟐CMD {"action": "invoke_agent", "agent_id": "agent-1"}
    ⟐CMD {"action": "delete_symbol", "id": "S1"}
    ⟐CMD {"action": "query_symbols", "query": "test"}
    """

    interpreter = CommandInterpreter()
    results = interpreter.run(payload)

    assert [item["action"] for item in results] == [
        "store_symbol",
        "load_symbol",
        "load_kit",
        "invoke_agent",
        "delete_symbol",
        "query_symbols",
    ]

    assert stored_symbols == {}
    assert isinstance(results[1]["result"][0], Symbol)
    assert results[2]["result"]["kit"] == "kit-1"
    assert results[3]["result"].name == "Agent"
    assert results[5]["result"]["status"] == "not_implemented"
