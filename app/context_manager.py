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

        print(f"token_budget: {token_budget}")
        print(f"sorted_syms: {sorted_syms}")
        print(f"self.symbols: {self.symbols}")
        
        packed = []
        tokens_used = 0

        for s in sorted_syms:
            triad = s.triad or []
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
        # Encode user prompt and calculate token budget
        user_tokens = len(self.encoder.encode(user_prompt))
        available_tokens = self.max_tokens - self.system_reserved - user_tokens
        symbol_token_budget = int(available_tokens * 0.5)
        history_token_budget = available_tokens - symbol_token_budget

        # Construct system block
        system_block = "\n".join(f"SYSTEM: {sp}" for sp in self.system_prompts)

        # Construct content blocks
        symbol_block = self.pack_symbols(symbol_token_budget)
        history_block = self.pack_history(history_token_budget)

        # Assemble final prompt
        sections = [
            system_block,
            "SYMBOLS:",
            symbol_block,
            "CHAT_HISTORY:",
            history_block,
            f"USER: {user_prompt}"
        ]

        # Log diagnostic information
        log.debug(
            "context_manager.prompt_built",
            system_prompts=len(self.system_prompts),
            symbol_characters=len(symbol_block),
            history_characters=len(history_block),
        )

        return "\n\n".join(sections)
