from app import config


def test_get_settings_uses_env(monkeypatch):
    monkeypatch.setenv("MODEL_PROVIDER", "openai")
    monkeypatch.setenv("MODEL_API_URL", "http://example.com")
    monkeypatch.setenv("MODEL_NAME", "test-model")

    config.get_settings.cache_clear()
    settings = config.get_settings()

    assert settings.model_provider == "openai"
    assert settings.model_api_url == "http://example.com"
    assert settings.model_name == "test-model"

    # Ensure caching returns same object
    assert config.get_settings() is settings
