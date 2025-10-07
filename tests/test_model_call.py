from types import SimpleNamespace


from app import model_call


class DummyResponse:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload or {"response": "ok"}
        self.text = text

    def json(self):
        return self._payload


def test_normalise_openai_response_content():
    assert model_call._normalise_openai_response_content("hello") == "hello"
    assert model_call._normalise_openai_response_content(None) == ""
    assert model_call._normalise_openai_response_content([
        {"text": "part1"},
        {"text": "part2"},
    ]) == "part1part2"
    assert model_call._normalise_openai_response_content(123) == "123"


def test_call_local_model(monkeypatch):
    responses = []

    def fake_post(url, json, timeout):
        responses.append((url, json, timeout))
        return DummyResponse()

    monkeypatch.setattr(model_call.requests, "post", fake_post)

    result = model_call._call_local_model("test prompt")

    assert result == "ok"
    assert responses[0][1]["prompt"] == "test prompt"


def test_model_call_routes_to_local(monkeypatch):
    monkeypatch.setattr(model_call, "_call_local_model", lambda prompt: "local-result")
    monkeypatch.setattr(model_call.settings, "model_provider", "local", raising=False)

    result = model_call.model_call("prompt")
    assert result == "local-result"


def test_model_call_routes_to_openai(monkeypatch):
    monkeypatch.setattr(model_call, "_call_openai_model", lambda prompt: "openai-result")
    monkeypatch.setattr(model_call.settings, "model_provider", "openai", raising=False)
    monkeypatch.setattr(model_call.settings, "openai_api_key", "dummy", raising=False)

    result = model_call.model_call("prompt")
    assert result == "openai-result"
