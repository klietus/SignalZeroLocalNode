"""Application configuration utilities."""
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Literal, Optional

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    """Settings loaded from environment variables."""

    model_provider: Literal["local", "openai"] = "local"
    model_api_url: str = "http://localhost:11434/api/generate"
    model_name: str = "deepseek-r1:8b"
    model_num_predict: int = 48

    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"
    openai_base_url: Optional[str] = None
    openai_temperature: float = 0.0
    openai_max_output_tokens: int = 1028

    @classmethod
    def from_env(cls) -> "Settings":
        """Construct settings from environment variables."""

        def _optional(name: str) -> Optional[str]:
            value = os.getenv(name)
            return value if value not in {None, ""} else None

        data = {
            "model_provider": os.getenv("MODEL_PROVIDER", cls.model_provider),
            "model_api_url": os.getenv("MODEL_API_URL", cls.model_api_url),
            "model_name": os.getenv("MODEL_NAME", cls.model_name),
            "openai_api_key": _optional("OPENAI_API_KEY"),
            "openai_model": os.getenv("OPENAI_MODEL", cls.openai_model),
            "openai_base_url": _optional("OPENAI_BASE_URL"),
        }

        if (value := os.getenv("MODEL_NUM_PREDICT")) is not None:
            data["model_num_predict"] = int(value)

        if (value := os.getenv("OPENAI_TEMPERATURE")) is not None:
            data["openai_temperature"] = float(value)

        if (value := os.getenv("OPENAI_MAX_OUTPUT_TOKENS")) is not None:
            data["openai_max_output_tokens"] = int(value)

        return cls(**data)


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""

    return Settings.from_env()
