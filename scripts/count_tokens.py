# count_tokens.py

from __future__ import annotations

import sys
from typing import Callable, Optional
from pathlib import Path

MODE = "openai"  # or "llama"

try:  # pragma: no cover - optional dependency
    import tiktoken
except Exception:  # pragma: no cover - optional dependency
    tiktoken = None  # type: ignore

_tokenizer: Optional[Callable[[str], list[int]]] = None


def _load_openai_tokenizer() -> Callable[[str], list[int]]:
    if tiktoken is None:
        raise ImportError("tiktoken is required when MODE is 'openai'")
    try:
        encoding = tiktoken.get_encoding("cl100k_base")
    except Exception:  # pragma: no cover - network resilience
        return lambda text: [len(token) for token in text.split()]
    return encoding.encode


def _load_llama_tokenizer() -> Callable[[str], list[int]]:
    from llama_tokenizer import Tokenizer  # type: ignore

    tokenizer = Tokenizer()
    return lambda text: list(tokenizer.tokenize(text))


def _resolve_tokenizer() -> Callable[[str], list[int]]:
    global _tokenizer
    if _tokenizer is not None:
        return _tokenizer

    if MODE == "openai":
        _tokenizer = _load_openai_tokenizer()
    elif MODE == "llama":
        _tokenizer = _load_llama_tokenizer()
    else:
        raise ValueError("Unknown tokenizer mode.")

    return _tokenizer


def count_tokens(text: str) -> None:
    tokenizer = _resolve_tokenizer()
    tokens = tokenizer(text)
    print(f"Token count: {len(tokens)}")


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Usage: python count_tokens.py <file.txt>")
        return 1
    path = Path(argv[1])
    text = path.read_text(encoding="utf-8")
    count_tokens(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
