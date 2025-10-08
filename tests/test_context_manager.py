from app.context_manager import ContextManager


class DummySymbol:
    def __init__(self, sid: str, name: str, triad=None, macro="", linked_patterns=None):
        self.id = sid
        self.name = name
        self.triad = triad or ["t1", "t2"]
        self.description = "desc"
        self.macro = macro
        self.linked_patterns = linked_patterns or []


class DummyAgent:
    def __init__(self, aid: str, name: str, triad=None, activation_conditions=None):
        self.id = aid
        self.name = name
        self.triad = triad or ["t1", "t2"]
        self.activation_conditions = activation_conditions or []


def test_pack_symbols_respects_budget():
    ctx = ContextManager(max_tokens=200, system_reserved=0)
    sym1 = DummySymbol("s1", "First", macro="macro one", linked_patterns=["p1", "p2"])
    sym2 = DummySymbol("s2", "Second", macro="macro two", linked_patterns=["p3", "p4"])

    ctx.add_symbol(sym1, relevance=0.9)
    ctx.add_symbol(sym2, relevance=0.1)

    packed = ctx.pack_symbols(30)
    assert "s1" in packed
    assert "s2" not in packed

def test_pack_history_includes_latest():
    ctx = ContextManager(max_tokens=200, system_reserved=0)
    ctx.add_history("user", "hello")
    ctx.add_history("assistant", "hi")

    packed = ctx.pack_history(20)
    assert "USER: hello" in packed
    assert "ASSISTANT: hi" in packed


def test_build_prompt_structure():
    ctx = ContextManager(max_tokens=200, system_reserved=10)
    ctx.add_system_prompt("system message")
    ctx.add_agent(type("Agent", (), {"id": "a-1", "name": "Agent One"})())
    ctx.add_symbol(DummySymbol("s1", "Name", macro="macro"))
    ctx.add_history("user", "hello")

    prompt = ctx.build_prompt("do work")
    assert "SYSTEM: system message" in prompt
    assert "AGENTS:" in prompt
    assert "a-1" in prompt
    assert "SYMBOLS:" in prompt
    assert "CHAT_HISTORY:" in prompt
    assert "USER: do work" in prompt
