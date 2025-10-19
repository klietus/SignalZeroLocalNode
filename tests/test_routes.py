import asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import routes


import pytest


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(routes.router)
    return TestClient(app)


def test_query_endpoint(client, monkeypatch):
    monkeypatch.setattr(routes, "run_query", lambda query, session_id: {"reply": "done", "session": session_id})

    response = client.post("/query", json={"query": "hello", "session_id": "abc"})
    assert response.status_code == 200
    assert response.json()["reply"] == "done"


def test_get_symbols(client, monkeypatch):
    monkeypatch.setattr(routes.symbol_store, "get_symbols", lambda **kwargs: ["sym1", "sym2"])

    response = client.get("/symbols")
    assert response.status_code == 200
    assert response.json() == ["sym1", "sym2"]


def test_get_symbol_by_id(client, monkeypatch):
    monkeypatch.setattr(routes.symbol_store, "get_symbol", lambda sid: {"id": sid})

    response = client.get("/symbol/test")
    assert response.status_code == 200
    assert response.json() == {"id": "test"}


def test_get_symbol_not_found(client, monkeypatch):
    monkeypatch.setattr(routes.symbol_store, "get_symbol", lambda sid: None)

    response = client.get("/symbol/missing")
    assert response.status_code == 404


def test_put_symbol(client, monkeypatch):
    recorded = {}

    def fake_put(symbol_id, symbol):
        recorded["payload"] = (symbol_id, symbol)
        return "stored"

    monkeypatch.setattr(routes.symbol_store, "put_symbol", fake_put)

    payload = {"id": "sym", "name": "Symbol"}
    response = client.put("/inject/sym", json=payload)

    assert response.status_code == 200
    assert response.json() == {"status": "stored"}
    assert recorded["payload"][0] == "sym"


def test_bulk_put_symbols(monkeypatch):
    calls = {}

    def fake_bulk(symbols):
        calls["symbols"] = symbols
        return "bulk"

    monkeypatch.setattr(routes.symbol_store, "put_symbols_bulk", fake_bulk)

    payload = [routes.Symbol(id="s1"), routes.Symbol(id="s2")]
    result = asyncio.run(routes.bulk_put_symbols(payload))

    assert result == {"status": "bulk"}
    assert [s.id for s in calls["symbols"]] == ["s1", "s2"]


def test_list_local_domains(client, monkeypatch):
    monkeypatch.setattr(routes.symbol_store, "get_domains", lambda: ["local", "domains"])

    response = client.get("/domains")
    assert response.status_code == 200
    assert response.json() == ["local", "domains"]


def test_list_local_domains_error(client, monkeypatch):
    def boom():
        raise RuntimeError("uh oh")

    monkeypatch.setattr(routes.symbol_store, "get_domains", boom)

    response = client.get("/domains")
    assert response.status_code == 500
    assert response.json()["detail"] == "Failed to retrieve local domains"


def test_list_external_domains(client, monkeypatch):
    async def fake_to_thread(func, *args, **kwargs):
        return func(*args, **kwargs)

    monkeypatch.setattr(routes.asyncio, "to_thread", fake_to_thread)
    monkeypatch.setattr(
        routes.symbol_sync,
        "fetch_domains_from_external_store",
        lambda: ["a", "b"],
    )

    response = client.get("/external/domains")
    assert response.status_code == 200
    assert response.json() == ["a", "b"]


def test_list_external_domains_error(client, monkeypatch):
    async def fake_to_thread(func, *args, **kwargs):
        return func(*args, **kwargs)

    monkeypatch.setattr(routes.asyncio, "to_thread", fake_to_thread)

    def boom():
        raise routes.symbol_sync.ExternalSymbolStoreError("nope")

    monkeypatch.setattr(routes.symbol_sync, "fetch_domains_from_external_store", boom)

    response = client.get("/external/domains")
    assert response.status_code == 502
    assert response.json()["detail"] == "Failed to retrieve external domains"


def test_sync_symbols_route_success(client, monkeypatch):
    recorded = {}

    def fake_sync(**kwargs):
        recorded["kwargs"] = kwargs
        return routes.symbol_sync.SyncResult(fetched=2, stored=2, new=1, updated=1, pages=1)

    async def fake_to_thread(func, *args, **kwargs):
        return func(*args, **kwargs)

    monkeypatch.setattr(routes.symbol_sync, "sync_symbols_from_external_store", fake_sync)
    monkeypatch.setattr(routes.asyncio, "to_thread", fake_to_thread)

    payload = {"symbol_domain": "root", "symbol_tag": "system", "limit": 10}
    response = client.post("/sync/symbols", json=payload)

    assert response.status_code == 200
    assert response.json() == {"fetched": 2, "stored": 2, "new": 1, "updated": 1, "pages": 1}
    assert recorded["kwargs"] == {
        "symbol_domain": "root",
        "symbol_tag": "system",
        "limit": 10,
    }


def test_sync_symbols_route_external_error(client, monkeypatch):
    def fake_sync(**kwargs):
        raise routes.symbol_sync.ExternalSymbolStoreError("boom")

    async def fake_to_thread(func, *args, **kwargs):
        return func(*args, **kwargs)

    monkeypatch.setattr(routes.symbol_sync, "sync_symbols_from_external_store", fake_sync)
    monkeypatch.setattr(routes.asyncio, "to_thread", fake_to_thread)

    response = client.post("/sync/symbols", json={})

    assert response.status_code == 502
    assert response.json()["detail"] == "Failed to sync symbols from external store"


def test_sync_symbols_route_bad_limit(client, monkeypatch):
    def fake_sync(**kwargs):
        raise ValueError("limit must be greater than zero")

    async def fake_to_thread(func, *args, **kwargs):
        return func(*args, **kwargs)

    monkeypatch.setattr(routes.symbol_sync, "sync_symbols_from_external_store", fake_sync)
    monkeypatch.setattr(routes.asyncio, "to_thread", fake_to_thread)

    response = client.post("/sync/symbols", json={"limit": 5})

    assert response.status_code == 400
    assert response.json()["detail"] == "limit must be greater than zero"
