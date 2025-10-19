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
        assert request.url.path == "/symbol"
        assert request.url.params.get("symbol_domain") == "root"
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
        result = symbol_sync.sync_symbols_from_external_store(
            limit=2, client=client, symbol_domain="root"
        )

    assert result.fetched == 3
    assert result.stored == 3
    assert result.new == 2
    assert result.updated == 1
    assert result.pages == 2
    assert mock_store == [["remote-existing", "remote-new"], ["remote-second"]]


def test_sync_symbols_cursor_url(mock_store):
    responses = [
        {"symbols": [{"id": "remote-a"}], "next": "/symbol?last_symbol_id=remote-a&limit=7"},
        {"symbols": [{"id": "remote-b"}]},
        {"symbols": []},
    ]

    calls = {"index": 0}

    def handler(request):
        assert request.url.path == "/symbol"
        assert request.url.params.get("symbol_domain") == "root"
        call_index = calls["index"]
        calls["index"] += 1
        query_text = request.url.query.decode()
        if call_index == 0:
            assert "limit=7" in query_text
            assert "last_symbol_id" not in query_text
        elif call_index == 1:
            assert "limit=7" in query_text
            assert "last_symbol_id=remote-a" in query_text
        elif call_index == 2:
            assert "last_symbol_id=remote-b" in query_text

        payload = responses[min(call_index, len(responses) - 1)]
        return httpx.Response(200, json=payload)

    transport = httpx.MockTransport(handler)

    with symbol_sync.ExternalSymbolStoreClient(
        "https://example.com", transport=transport
    ) as client:
        result = symbol_sync.sync_symbols_from_external_store(
            limit=7, client=client, symbol_domain="root"
        )

    assert result.fetched == 2
    assert result.stored == 2
    assert result.new == 2
    assert result.updated == 0
    assert result.pages == 2


def test_sync_symbols_all_domains(mock_store):
    domain_pages = {
        "root": [[{"id": "root-1"}], []],
        "diagnostics": [[{"id": "diag-1"}], []],
    }

    call_counts = {key: 0 for key in domain_pages}

    def handler(request):
        if request.url.path == "/domains":
            return httpx.Response(200, json=list(domain_pages.keys()))

        assert request.url.path == "/symbol"
        domain = request.url.params.get("symbol_domain")
        assert domain in domain_pages
        call_index = call_counts[domain]
        call_counts[domain] += 1
        payloads = domain_pages[domain]
        payload = payloads[call_index] if call_index < len(payloads) else []
        return httpx.Response(200, json={"symbols": payload})

    transport = httpx.MockTransport(handler)

    with symbol_sync.ExternalSymbolStoreClient(
        "https://example.com", transport=transport
    ) as client:
        result = symbol_sync.sync_symbols_from_external_store(limit=5, client=client)

    assert result.fetched == 2
    assert result.stored == 2
    assert result.new == 2
    assert result.updated == 0
    assert result.pages == 2
    assert mock_store == [["root-1"], ["diag-1"]]


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


@pytest.mark.parametrize(
    "cursor,expected_id,expected_limit",
    [
        (None, None, None),
        ("", None, None),
        ("remote-id", "remote-id", None),
        ("last_symbol_id=remote-id", "remote-id", None),
        ("/symbol?last_symbol_id=remote-id&limit=5", "remote-id", 5),
        ("https://example.com/symbol?cursor=remote-id", "remote-id", None),
        ("cursor=remote-id&limit=12", "remote-id", 12),
    ],
)
def test_decode_cursor_variants(cursor, expected_id, expected_limit):
    result = symbol_sync._decode_cursor(cursor)
    assert result == (expected_id, expected_limit)
