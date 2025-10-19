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
            payload = pages[index]
            # Return object payload with cursor to exercise parsing flexibility
            return httpx.Response(200, json={"symbols": payload, "last_symbol_id": payload[-1]["id"]})
        return httpx.Response(200, json={"symbols": [], "last_symbol_id": None})

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


def test_list_domains_success():
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=["root", "diag"]))

    with symbol_sync.ExternalSymbolStoreClient(
        "https://example.com", transport=transport
    ) as client:
        domains = client.list_domains()

    assert domains == ["root", "diag"]


def test_list_domains_invalid_payload():
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"oops": 1}))

    with symbol_sync.ExternalSymbolStoreClient(
        "https://example.com", transport=transport
    ) as client:
        with pytest.raises(symbol_sync.ExternalSymbolStoreError):
            client.list_domains()


def test_query_symbols_handles_bad_request(monkeypatch):
    transport = httpx.MockTransport(
        lambda request: httpx.Response(400, text="missing filter")
    )

    with symbol_sync.ExternalSymbolStoreClient(
        "https://example.com", transport=transport
    ) as client:
        with pytest.raises(ValueError) as exc_info:
            client.query_symbols()

    assert "missing filter" in str(exc_info.value)


def test_fetch_domains_from_external_store(monkeypatch):
    settings = type("Settings", (), {"symbol_store_base_url": "https://example.com", "symbol_store_timeout": 3})
    monkeypatch.setattr(symbol_sync, "get_settings", lambda: settings)

    instances = []

    class DummyClient:
        def __init__(self, base_url, timeout):
            self.base_url = base_url
            self.timeout = timeout
            self.closed = False
            instances.append(self)

        def list_domains(self):
            return ["root"]

        def close(self):
            self.closed = True

    monkeypatch.setattr(symbol_sync, "ExternalSymbolStoreClient", DummyClient)

    domains = symbol_sync.fetch_domains_from_external_store()

    assert domains == ["root"]
    assert len(instances) == 1
    assert instances[0].base_url == "https://example.com"
    assert instances[0].timeout == 3
    assert instances[0].closed is True


def test_fetch_domains_from_external_store_error(monkeypatch):
    settings = type("Settings", (), {"symbol_store_base_url": "https://example.com", "symbol_store_timeout": 3})
    monkeypatch.setattr(symbol_sync, "get_settings", lambda: settings)

    instances = []

    class DummyClient:
        def __init__(self, *args, **kwargs):
            instances.append(self)
            self.closed = False

        def list_domains(self):
            raise symbol_sync.ExternalSymbolStoreError("boom")

        def close(self):
            self.closed = True

    monkeypatch.setattr(symbol_sync, "ExternalSymbolStoreClient", DummyClient)

    with pytest.raises(symbol_sync.ExternalSymbolStoreError):
        symbol_sync.fetch_domains_from_external_store()

    assert instances[0].closed is True
