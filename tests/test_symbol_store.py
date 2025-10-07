from collections import defaultdict
from pathlib import Path

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
