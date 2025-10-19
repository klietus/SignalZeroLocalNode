import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("EMBEDDING_INDEX_BACKEND", "memory")


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


class _StubEncoding:
    def encode(self, text: str) -> list[int]:
        if not text:
            return []
        return [len(part.encode("utf-8")) for part in text.split()]


@pytest.fixture(autouse=True)
def _stub_context_manager_encoder(monkeypatch):
    """Prevent tiktoken network access when instantiating ContextManager."""

    def _fake_get_encoding(name: str):  # pragma: no cover - simple test shim
        return _StubEncoding()

    monkeypatch.setattr("app.context_manager.tiktoken.get_encoding", _fake_get_encoding)
    yield
