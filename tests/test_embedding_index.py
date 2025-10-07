import importlib
from types import SimpleNamespace

import pytest

from app import embedding_index
from app import symbol_store


class DummyModel:
    def encode(self, text: str):
        return [float(len(text))]


def test_build_and_search(monkeypatch):
    monkeypatch.setenv("EMBEDDING_INDEX_BACKEND", "memory")
    importlib.reload(embedding_index)

    monkeypatch.setattr(embedding_index, "model", DummyModel())
    monkeypatch.setattr(embedding_index, "index", embedding_index._InMemoryIndex(1))
    embedding_index.symbol_index_map = {}
    embedding_index.index_data = []

    symbols = [
        SimpleNamespace(id="s1", macro="alpha"),
        SimpleNamespace(id="s2", macro="beta"),
    ]

    monkeypatch.setattr(symbol_store, "get_symbols", lambda domain, tag, start, limit: symbols)

    embedding_index.build_index()
    results = embedding_index.search("alpha", k=2)

    assert results[0][0] == "s1"
    assert results[0][1] == pytest.approx(0.0)
    assert {sid for sid, _ in results} == {"s1", "s2"}
