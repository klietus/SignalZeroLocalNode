import pytest

from app import agency_loop


def test_load_prompt_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        agency_loop._load_prompt(tmp_path / "missing.txt")


def test_build_context(monkeypatch):
    monkeypatch.setattr(agency_loop, "SHARED_PROMPTS", ["shared-a", "shared-b"])

    symbol = type("Symbol", (), {"id": "s1", "name": "Name", "triad": ["a"], "description": "desc", "macro": "macro", "linked_patterns": ["p1", "p2"], "invocations": ["i1", "i2"]})()
    ctx = agency_loop._build_context(
        base_history=[("user", "hi")],
        interim_history=[("assistant", "hello")],
        symbols=[symbol],
        phase_prompt="phase",
    )

    prompt = ctx.build_prompt("user prompt")
    assert "SYSTEM: shared-a" in prompt
    assert "USER: hi" in prompt


def test_run_phase_invokes_model(monkeypatch):
    class DummyContext:
        def __init__(self):
            self.prompt = None

        def build_prompt(self, user_prompt):
            self.prompt = user_prompt
            return "built"

    def fake_build_context(*args, **kwargs):
        return DummyContext()

    monkeypatch.setattr(agency_loop, "_build_context", fake_build_context)
    monkeypatch.setattr(agency_loop, "model_call", lambda prompt: f"called:{prompt}")

    reply = agency_loop._run_phase(
        "phase",
        "prompt",
        iteration=1,
        timestamp="now",
        base_history=[],
        interim_history=[],
        symbols=[],
    )

    assert reply == "called:built"
