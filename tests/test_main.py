from fastapi.testclient import TestClient

from app import main


def test_root_endpoint(monkeypatch):
    calls = {"loaded": 0, "built": 0, "encrypted": 0}

    monkeypatch.setattr(main, "load_symbol_store_if_empty", lambda: calls.__setitem__("loaded", calls["loaded"] + 1))
    monkeypatch.setattr(main, "build_index", lambda: calls.__setitem__("built", calls["built"] + 1))
    monkeypatch.setattr(main, "initialize_encryption", lambda: calls.__setitem__("encrypted", calls["encrypted"] + 1))

    with TestClient(main.app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"status": "SignalZero Local Node Live"}
    assert calls["loaded"] >= 1
    assert calls["built"] >= 1
    assert calls["encrypted"] >= 1
