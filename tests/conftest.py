import pytest


@pytest.fixture(autouse=True)
def _set_test_environment(monkeypatch):
    """Ensure predictable environment variables for tests."""

    monkeypatch.setenv("EMBEDDING_INDEX_BACKEND", "memory")
    # Provide defaults that avoid network calls during tests.
    monkeypatch.delenv("MODEL_PROVIDER", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_TEMPERATURE", raising=False)
    monkeypatch.delenv("OPENAI_MAX_OUTPUT_TOKENS", raising=False)
    yield
