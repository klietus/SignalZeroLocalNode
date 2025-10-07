"""Conversation context assembly utilities."""
from __future__ import annotations

from typing import List

import structlog

from app.logging_config import configure_logging


configure_logging()
log = structlog.get_logger(__name__)

try:  # pragma: no cover - optional dependency
    import tiktoken
except Exception:  # pragma: no cover - optional dependency
    tiktoken = None  # type: ignore


class _SimpleEncoder:
    def encode(self, text: str) -> List[int]:
        return [len(token) for token in text.split()]


def _get_encoder():
    if tiktoken is None:
        return _SimpleEncoder()
    try:
        return tiktoken.get_encoding("cl100k_base")
    except Exception:  # pragma: no cover - network resilience
        return _SimpleEncoder()


class ContextManager:
    def __init__(self, max_tokens=8192, system_reserved=1000):
        self.max_tokens = max_tokens
        self.system_reserved = system_reserved
        self.encoder = _get_encoder()
        self.symbols = []  # list of dicts with keys: id, triad, description, relevance
        self.history = []  # list of (role, content) tuples
        self.system_prompts = []  # ordered system prompts
        log.debug(
            "context_manager.initialised",
            max_tokens=max_tokens,
            system_reserved=system_reserved,
        )

    def add_system_prompt(self, content):
        self.system_prompts.append(content)
        log.debug(
            "context_manager.system_prompt_added",
            prompt_length=len(content),
            total=len(self.system_prompts),
        )

    def add_symbol(self, symbol, relevance=1.0):
        setattr(symbol, "relevance", relevance)
        self.symbols.append(symbol)
        log.debug("context_manager.symbol_added", symbol_id=getattr(symbol, "id", None))

    def add_history(self, role, content):
        self.history.append((role, content))
        log.debug("context_manager.history_added", role=role, length=len(content))

    def pack_symbols(self, token_budget):
        sorted_syms = sorted(self.symbols, key=lambda x: -getattr(x, "relevance", 0.0))

        packed = []
        tokens_used = 0

        for s in sorted_syms:
            triad = s.triad or []
            desc = s.description or ""
            macro = s.macro or ""

            line = f"{s.id} | {s.name} |{' '.join(triad)} | {macro}"
            t = len(self.encoder.encode(line))
            if tokens_used + t > token_budget:
                break
            packed.append(line)
            tokens_used += t

        return "\n".join(packed)

    def pack_history(self, token_budget):
        packed = []
        tokens_used = 0

        for role, content in reversed(self.history):  # newest first
            block = f"{role.upper()}: {content}"
            t = len(self.encoder.encode(block))
            if tokens_used + t > token_budget:
                break
            packed.insert(0, block)  # maintain order
            tokens_used += t

        return "\n".join(packed)

    def build_prompt(self, user_prompt):
        prompt_parts = []
        for sp in self.system_prompts:
            prompt_parts.append(f"SYSTEM: {sp}")
        available = self.max_tokens - self.system_reserved - len(self.encoder.encode(user_prompt))
        symbol_tokens = int(available * 0.5)
        history_tokens = available - symbol_tokens

        sym = self.pack_symbols(symbol_tokens)
        hist = self.pack_history(history_tokens)

        prompt_parts.append("SYMBOLS:")
        prompt_parts.append(sym)
        prompt_parts.append("CHAT_HISTORY:")
        prompt_parts.append(hist)
        prompt_parts.append(f"USER: {user_prompt}")
        log.debug(
            "context_manager.prompt_built",
            system_prompts=len(self.system_prompts),
            symbol_characters=len(sym),
            history_characters=len(hist),
        )
        return "\n\n".join(prompt_parts)
