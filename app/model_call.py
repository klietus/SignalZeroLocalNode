"""Utilities for invoking the configured language model."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import requests

from app.config import get_settings

settings = get_settings()
_openai_client: Optional[Any] = None

if settings.model_provider == "openai":
    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover - defensive import guard
        raise ImportError(
            "The 'openai' package is required when MODEL_PROVIDER=openai. "
            "Install it via 'pip install openai'."
        ) from exc
else:  # pragma: no cover - defensive assignment for type checkers
    OpenAI = None  # type: ignore[assignment]


def _call_local_model(prompt: str) -> str:
    """Call the locally hosted model REST API."""

    payload: Dict[str, Any] = {
        "model": settings.model_name,
        "prompt": prompt,
        "stream": False,
        "num_predict": settings.model_num_predict,
    }

    response = requests.post(settings.model_api_url, json=payload, timeout=300)
    if response.status_code != 200:
        raise RuntimeError(
            f"Model API failed: {response.status_code} - {response.text}"
        )

    data = response.json()
    return data["response"]


def _normalise_openai_response_content(content: Any) -> str:
    """Normalise OpenAI response content into a plain string."""

    if content is None:
        return ""

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts: List[str] = []
        for item in content:
            if isinstance(item, dict) and "text" in item:
                parts.append(str(item["text"]))
            else:
                parts.append(str(item))
        return "".join(parts)

    return str(content)


def _call_openai_model(prompt: str) -> str:
    """Call the OpenAI API using the configured model."""

    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY must be set when MODEL_PROVIDER=openai")

    global _openai_client
    if _openai_client is None:
        client_kwargs: Dict[str, Any] = {"api_key": settings.openai_api_key}
        if settings.openai_base_url:
            client_kwargs["base_url"] = settings.openai_base_url
        _openai_client = OpenAI(**client_kwargs)  # type: ignore[call-arg]

    response = _openai_client.chat.completions.create(  # type: ignore[union-attr]
        model=settings.openai_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=settings.openai_temperature,
        max_tokens=settings.openai_max_output_tokens,
    )

    if not response.choices:
        raise RuntimeError("OpenAI response contained no choices")

    message = response.choices[0].message
    return _normalise_openai_response_content(message.content)


def model_call(prompt: str) -> str:
    """Call the configured model provider with the supplied prompt."""

    print("sending: " + prompt)

    if settings.model_provider == "openai":
        result = _call_openai_model(prompt)
    elif settings.model_provider == "local":
        result = _call_local_model(prompt)
    else:  # pragma: no cover - defensive branch
        raise ValueError(
            f"Unsupported MODEL_PROVIDER configured: {settings.model_provider}"
        )

    print("received:" + result)
    return result
