from collections import defaultdict

from app import symbol_store
from app.types import Symbol


class FakeRedis:
    def __init__(self):
        self.store = {}
        self.sets = defaultdict(set)

    def set(self, key, value):
        self.store[key] = value

    def get(self, key):
        return self.store.get(key)

    def mget(self, keys):
        return [self.store.get(key) for key in keys]

    def keys(self, pattern):  # noqa: ARG002 - pattern unused in fake
        return list(self.store.keys())

    def sadd(self, name, value):
        self.sets[name].add(value)

    def smembers(self, name):
        return set(self.sets.get(name, set()))

    def delete(self, key):
        return 1 if self.store.pop(key, None) is not None else 0

    def scan_iter(self, match=None, count=None):  # noqa: ARG002 - compatibility helper
        for key in list(self.store.keys()):
            if match is None:
                yield key
            elif match.endswith("*") and key.startswith(match[:-1]):
                yield key
            elif key == match:
                yield key

    # Pipeline support -------------------------------------------------
    def pipeline(self):
        return self

    def execute(self):
        return []


def test_load_symbol_store(monkeypatch, tmp_path):
    fake = FakeRedis()
    monkeypatch.setattr(symbol_store, "r", fake)
    monkeypatch.setattr(symbol_store.embedding_index, "add_symbol", lambda symbol: None)

    catalog = {
        "symbols": [
            {
                "id": "s1",
                "macro": "macro",
                "symbol_domain": "domain",
            }
        ]
    }
    path = tmp_path / "symbols.json"
    path.write_text(symbol_store.json.dumps(catalog))

    symbol_store.load_symbol_store_if_empty(path=str(path))
    stored = symbol_store.get_symbol("s1")
    assert stored.id == "s1"


def test_load_symbol_store_merges_existing_data(monkeypatch, tmp_path):
    fake = FakeRedis()
    monkeypatch.setattr(symbol_store, "r", fake)
    monkeypatch.setattr(symbol_store.embedding_index, "add_symbol", lambda symbol: None)
    calls = {"agents": 0, "kits": 0}

    def _load_agents(path="data/agents.json"):
        calls["agents"] += 1
        return 0

    def _load_kits(path="data/kits.min.json"):
        calls["kits"] += 1
        return 0

    monkeypatch.setattr(symbol_store, "load_agents", _load_agents)
    monkeypatch.setattr(symbol_store, "load_kits", _load_kits)

    existing = Symbol(id="existing", macro="original", symbol_domain="domain")
    fake.set(f"symbol:{existing.id}", existing.model_dump_json())

    catalog = {
        "symbols": [
            {
                "id": "existing",
                "macro": "updated",
                "symbol_domain": "domain",
            },
            {
                "id": "new",
                "macro": "macro",
                "symbol_domain": "domain",
            }
        ]
    }

    path = tmp_path / "symbols.json"
    path.write_text(symbol_store.json.dumps(catalog))

    symbol_store.load_symbol_store_if_empty(path=str(path))

    stored_existing = symbol_store.get_symbol("existing")
    stored_new = symbol_store.get_symbol("new")

    assert stored_existing is not None
    assert stored_existing.id == "existing"
    assert stored_existing.macro == "original"
    assert stored_new is not None
    assert stored_new.id == "new"
    assert calls == {"agents": 1, "kits": 1}


def test_put_and_get(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(symbol_store, "r", fake)
    recorded = []
    monkeypatch.setattr(symbol_store.embedding_index, "add_symbol", lambda symbol: recorded.append(symbol.id))

    symbol = Symbol(id="s1", macro="macro", symbol_domain="domain")
    status = symbol_store.put_symbol("s1", symbol)

    assert status == "stored"
    assert recorded == ["s1"]
    assert symbol_store.get_symbol("s1").id == "s1"
    assert symbol_store.get_domains() == ["domain"]


def test_bulk_put(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(symbol_store, "r", fake)
    recorded = []
    monkeypatch.setattr(symbol_store.embedding_index, "add_symbol", lambda symbol: recorded.append(symbol.id))

    symbols = [
        Symbol(id="s1", macro="one", symbol_domain="d1"),
        Symbol(id="s2", macro="two", symbol_domain="d2"),
    ]

    status = symbol_store.put_symbols_bulk(symbols)
    assert status == "bulk_stored"
    assert set(recorded) == {"s1", "s2"}

    listed = symbol_store.get_symbols(domain=None, tag=None, start=0, limit=10)
    assert {sym.id for sym in listed} == {"s1", "s2"}


def test_get_symbols_by_ids(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(symbol_store, "r", fake)
    monkeypatch.setattr(symbol_store.embedding_index, "add_symbol", lambda symbol: None)

    one = Symbol(id="s1", macro="one")
    two = Symbol(id="s2", macro="two")
    symbol_store.put_symbol(one.id, one)
    symbol_store.put_symbol(two.id, two)

    retrieved = symbol_store.get_symbols_by_ids(["s1", "missing", "s2"])

    assert [sym.id for sym in retrieved] == ["s1", "s2"]


def test_delete_symbol(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(symbol_store, "r", fake)
    monkeypatch.setattr(symbol_store.embedding_index, "add_symbol", lambda symbol: None)
    monkeypatch.setattr(symbol_store.embedding_index, "build_index", lambda: None)

    symbol = Symbol(id="s1", macro="macro", symbol_domain="domain")
    symbol_store.put_symbol("s1", symbol)

    status = symbol_store.delete_symbol("s1")
    assert status is True
    assert symbol_store.get_symbol("s1") is None


def test_load_kits_and_agents(monkeypatch, tmp_path):
    fake = FakeRedis()
    monkeypatch.setattr(symbol_store, "r", fake)
    monkeypatch.setattr(symbol_store.embedding_index, "add_symbol", lambda symbol: None)

    base_symbol = Symbol(id="SYM-1", macro="macro")
    symbol_store.put_symbol(base_symbol.id, base_symbol)

    kits_path = tmp_path / "kits.json"
    kits_path.write_text(symbol_store.json.dumps([
        {"kit": "kit-one", "triad": ["SYM-1"], "exec": ["SYM-1"], "anchor": "SYM-1", "note": "demo"}
    ]))

    agents_path = tmp_path / "agents.json"
    agents_path.write_text(symbol_store.json.dumps({
        "personas": [{"id": "AG-1", "name": "Agent"}]
    }))

    symbol_store.load_kits(path=str(kits_path))
    symbol_store.load_agents(path=str(agents_path))

    kit = symbol_store.get_kit("kit-one")
    assert kit is not None
    assert kit["triad"] and isinstance(kit["triad"][0], Symbol)
    assert kit["anchor"].id == "SYM-1"

    agent = symbol_store.get_agent("AG-1")
    assert agent is not None
    assert agent.name == "Agent"
