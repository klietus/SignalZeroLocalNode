import httpx
import pytest

from app import symbol_sync
from app.domain_types import Symbol


@pytest.fixture
def mock_store(monkeypatch):
    stored_batches = []

    def fake_put(symbols):
        stored_batches.append([s.id for s in symbols])
        return "ok"

    def fake_get(ids):
        return [Symbol(id="remote-existing")] if "remote-existing" in ids else []

    monkeypatch.setattr(symbol_sync.symbol_store, "put_symbols_bulk", fake_put)
    monkeypatch.setattr(symbol_sync.symbol_store, "get_symbols_by_ids", fake_get)
    return stored_batches


def test_sync_symbols_success(mock_store):
    pages = [
        [
            {"id": "remote-existing"},
            {"id": "remote-new"},
        ],
        [
            {"id": "remote-second"},
        ],
    ]

    calls = {"index": 0}

    def handler(request):
        index = calls["index"]
        calls["index"] += 1
        if index < len(pages):
            return httpx.Response(200, json=pages[index])
        return httpx.Response(200, json=[])

    transport = httpx.MockTransport(handler)

    with symbol_sync.ExternalSymbolStoreClient(
        "https://example.com", transport=transport
    ) as client:
        result = symbol_sync.sync_symbols_from_external_store(limit=2, client=client)

    assert result.fetched == 3
    assert result.stored == 3
    assert result.new == 2
    assert result.updated == 1
    assert result.pages == 2
    assert mock_store == [["remote-existing", "remote-new"], ["remote-second"]]


def test_sync_symbols_http_error(monkeypatch):
    transport = httpx.MockTransport(lambda request: httpx.Response(500))

    monkeypatch.setattr(symbol_sync.symbol_store, "put_symbols_bulk", lambda symbols: "ok")
    monkeypatch.setattr(symbol_sync.symbol_store, "get_symbols_by_ids", lambda ids: [])

    with symbol_sync.ExternalSymbolStoreClient(
        "https://example.com", transport=transport
    ) as client:
        with pytest.raises(symbol_sync.ExternalSymbolStoreError):
            symbol_sync.sync_symbols_from_external_store(client=client)


def test_sync_symbols_limit_validation(monkeypatch):
    monkeypatch.setattr(symbol_sync.symbol_store, "put_symbols_bulk", lambda symbols: "ok")
    monkeypatch.setattr(symbol_sync.symbol_store, "get_symbols_by_ids", lambda ids: [])

    with pytest.raises(ValueError):
        symbol_sync.sync_symbols_from_external_store(limit=0)
