import pytest

from app import inference


def test_load_prompt_phase_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        inference.load_prompt_phase("missing", workflow="user")


def test_run_query(monkeypatch):
    class DummyContextManager:
        def __init__(self):
            self.prompts = []
            self.history = []
            self.symbols = []

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

    class DummySymbol:
        def __init__(self, sid):
            self.id = sid
            self.macro = "macro"

    monkeypatch.setattr(inference, "ContextManager", DummyContextManager)
    monkeypatch.setattr(inference, "ChatHistory", DummyChatHistory)
    monkeypatch.setattr(inference.embedding_index, "search", lambda query, k: [("s1", 0.1)])
    monkeypatch.setattr(inference, "get_symbol", lambda sid: DummySymbol(sid))
    monkeypatch.setattr(inference, "model_call", lambda prompt: f"response for {prompt}")
    monkeypatch.setattr(inference, "load_prompt_phase", lambda phase_id, workflow="user": f"{workflow}:{phase_id}")
    monkeypatch.setattr(inference, "WORKFLOW_PHASES", [("phase1", "user"), ("phase2", "user")], raising=False)

    result = inference.run_query("what?", "session-1", k=1)

    assert result["reply"].startswith("response for")
    assert result["symbols_used"] == ["s1"]
    assert result["history_length"] == 2
