import pytest

from app import inference, command_utils
from app.types import Symbol


def test_load_prompt_phase_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        inference.load_prompt_phase("missing", workflow="user")


def test_run_query(monkeypatch):
    class DummyContextManager:
        instances = []

        def __init__(self):
            self.prompts = []
            self.history = []
            self.symbols = []
            DummyContextManager.instances.append(self)

        def add_system_prompt(self, prompt):
            self.prompts.append(prompt)

        def add_history(self, role, content):
            self.history.append((role, content))

        def add_symbol(self, symbol):
            self.symbols.append(symbol)

        def build_prompt(self, user_prompt):
            return f"prompt::{user_prompt}::{len(self.symbols)}"

    class DummyChatHistory:
        def __init__(self):
            self.messages = []

        def get_history(self, session_id):
            return list(self.messages)

        def append_message(self, session_id, role, content):
            self.messages.append((role, content))

    class DummyInterpreter:
        def __init__(self):
            self.inputs = []
            self.calls = 0

        def run(self, text):
            self.inputs.append(text)
            self.calls += 1
            if self.calls == 1:
                return [
                    {
                        "action": "load_symbol",
                        "result": [Symbol(id="s2", macro="macro")],
                        "payload": {"action": "load_symbol"},
                    }
                ]
            return []

    interpreter = DummyInterpreter()

    DummyContextManager.instances.clear()
    monkeypatch.setattr(inference, "ContextManager", DummyContextManager)
    monkeypatch.setattr(inference, "ChatHistory", DummyChatHistory)
    monkeypatch.setattr(inference.embedding_index, "search", lambda query, k: [("s1", 0.1)])
    symbols = {
        "s1": Symbol(id="s1", macro="macro"),
        "s2": Symbol(id="s2", macro="macro"),
    }
    monkeypatch.setattr(inference, "get_symbol", lambda sid: symbols.get(sid))
    monkeypatch.setattr(command_utils, "get_symbol", lambda sid: symbols.get(sid))
    monkeypatch.setattr(inference, "model_call", lambda prompt: f"response for {prompt}")
    monkeypatch.setattr(inference, "load_prompt_phase", lambda phase_id, workflow="user": f"{workflow}:{phase_id}")
    monkeypatch.setattr(inference, "WORKFLOW_PHASES", [("phase1", "user"), ("phase2", "user")], raising=False)
    monkeypatch.setattr(inference, "CommandInterpreter", lambda: interpreter)

    result = inference.run_query("what?", "session-1", k=1)

    assert result["reply"].startswith("response for")
    assert result["symbols_used"] == ["s1", "s2"]
    assert result["history_length"] == 3
    assert len(result["commands"]) == 1
    assert interpreter.inputs == [
        "response for prompt::what?::1",
        "response for prompt::what?::2",
    ]

    first_ctx, second_ctx = inference.ContextManager.instances[:2]
    assert len(first_ctx.symbols) == 1
    assert len(second_ctx.symbols) == 2
