"""Application configuration utilities."""
from functools import lru_cache
from typing import Literal, Optional

from dotenv import load_dotenv
from pydantic import BaseSettings, Field

load_dotenv()


class Settings(BaseSettings):
    """Settings loaded from environment variables."""

    model_provider: Literal["local", "openai"] = Field(
        default="local", env="MODEL_PROVIDER"
    )
    model_api_url: str = Field(
        default="http://localhost:11434/api/generate", env="MODEL_API_URL"
    )
    model_name: str = Field(default="llama3:8b-text-q5_K_M", env="MODEL_NAME")
    model_num_predict: int = Field(default=48, env="MODEL_NUM_PREDICT")

    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", env="OPENAI_MODEL")
    openai_base_url: Optional[str] = Field(default=None, env="OPENAI_BASE_URL")
    openai_temperature: float = Field(default=0.0, env="OPENAI_TEMPERATURE")
    openai_max_output_tokens: int = Field(
        default=256, env="OPENAI_MAX_OUTPUT_TOKENS"
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""

    return Settings()
