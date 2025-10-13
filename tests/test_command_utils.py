from app import command_utils
from app.domain_types import Symbol


def test_integrate_command_results_updates_symbols(monkeypatch):
    existing = Symbol(id="s1", macro="macro", lnk=["s2", "missing"])
    context_symbols = [existing]
    symbol_lookup = {existing.id: existing}

    linked_symbol = Symbol(id="s2", macro="macro")
    loaded_symbol = Symbol(id="s3", macro="macro")

    symbols_by_id = {"s2": linked_symbol}
    monkeypatch.setattr(command_utils, "get_symbol", lambda sid: symbols_by_id.get(sid))

    commands = [
        {
            "action": "load_symbol",
            "result": [loaded_symbol],
            "payload": {"action": "load_symbol"},
        },
        {
            "action": "recurse_graph",
            "result": {"status": "queued"},
            "payload": {"action": "recurse_graph"},
        },
        {
            "action": "noop",
            "result": {"status": "ok"},
            "payload": {"action": "noop"},
        },
    ]

    notes = command_utils.integrate_command_results(
        commands, context_symbols, symbol_lookup
    )

    assert {symbol.id for symbol in context_symbols} == {"s1", "s2", "s3"}
    assert symbol_lookup["s2"] is linked_symbol
    assert symbol_lookup["s3"] is loaded_symbol
    assert any("load_symbol" in note and "s3" in note for note in notes)
    assert any("recurse_graph" in note and "s2" in note for note in notes)
    assert any("noop" in note for note in notes)
