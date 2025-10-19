"""Conversation context assembly utilities."""
from __future__ import annotations

import structlog

from app.logging_config import configure_logging

import tiktoken

configure_logging()
log = structlog.get_logger(__name__)

class _FallbackEncoding:
    def encode(self, text: str) -> list[int]:
        # Whitespace-delimited fallback to approximate token counting offline.
        if not text:
            return []
        return [len(token.encode("utf-8")) for token in text.split()]


def _get_encoder():
    try:
        return tiktoken.get_encoding("cl100k_base")
    except Exception as exc:  # pragma: no cover - exercised in offline test environments
        log.warning("context_manager.encoder_fallback", error=str(exc))
        return _FallbackEncoding()


class ContextManager:
    def __init__(self, max_tokens=4096, system_reserved=1000):
        self.max_tokens = max_tokens
        self.system_reserved = system_reserved
        self.encoder = _get_encoder()
        self.symbols = []  # list of dicts with keys: id, triad, description, relevance
        self.agents = []  # list of agent personas to include in context
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

    def add_agent(self, agent):
        self.agents.append(agent)
        log.debug("context_manager.agent_added", agent_id=getattr(agent, "id", None))

    def add_history(self, role, content):
        self.history.append((role, content))
        log.debug("context_manager.history_added", role=role, length=len(content))

    def pack_symbols(self, token_budget):
        sorted_syms = sorted(self.symbols, key=lambda x: -getattr(x, "relevance", 0.0))

        packed = []
        tokens_used = 0

        for s in sorted_syms:
            triad = s.triad or []
            macro = s.macro or ""
            linked_patterns = " | ".join(s.linked_patterns or [])
            invocations = " | ".join(s.invocations or [])
            line = f"{s.id} | {s.name} |{' '.join(triad)} | {macro} | {invocations} | {linked_patterns}"
            t = len(self.encoder.encode(line))
            if tokens_used + t > token_budget:
                break
            packed.append(line)
            tokens_used += t

        return "\n".join(packed)

    def pack_agents(self, token_budget):
        packed = []
        tokens_used = 0

        for agent in self.agents:
            agent_id = getattr(agent, "id", None)
            if not agent_id:
                continue
            name = getattr(agent, "name", "")
            triad = " - ".join( getattr(agent, "triad", []))
            description = getattr(agent, "description", "")
            activation = " - ".join(getattr(agent, "activation_conditions", []))
            line = " | ".join(filter(None, [agent_id, name, description, triad, activation]))
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

        # Determine budgeting weights for each section
        weights = {}
        if self.agents:
            weights["agents"] = 0.2
        if self.symbols:
            weights["symbols"] = 0.5
        if self.history:
            weights["history"] = 0.3

        total_weight = sum(weights.values())
        budgets = {"agents": 0, "symbols": 0, "history": 0}
        if available_tokens > 0 and total_weight > 0:
            # Normalise weights so they sum to 1
            normalised = {
                key: weight / total_weight for key, weight in weights.items()
            }

            allocated = 0
            for key, weight in normalised.items():
                token_budget = int(available_tokens * weight)
                budgets[key] = token_budget
                allocated += token_budget

            # Distribute any rounding remainder
            remainder = available_tokens - allocated
            for key in ("agents", "symbols", "history"):
                if remainder <= 0:
                    break
                if key in normalised:
                    budgets[key] += 1
                    remainder -= 1

        agent_token_budget = budgets["agents"]
        symbol_token_budget = budgets["symbols"]
        history_token_budget = budgets["history"]

        log.debug("context_manager.budgets", budgets=budgets)

        # Construct system block
        system_block = "\n".join(f"SYSTEM: {sp}" for sp in self.system_prompts)

        # Construct content blocks
        agent_block = self.pack_agents(agent_token_budget)
        symbol_block = self.pack_symbols(symbol_token_budget)
        history_block = self.pack_history(history_token_budget)

        log.debug("context_manager.system_block.tokens", tokens=len(self.encoder.encode(system_block)))
        log.debug("context_manager.agent_block.tokens", tokens=len(self.encoder.encode(agent_block)))
        log.debug("context_manager.symbol_block.tokens", tokens=len(self.encoder.encode(symbol_block)))
        log.debug("context_manager.history_block.tokens", tokens=len(self.encoder.encode(history_block)))

        # Assemble final prompt
        sections = [
            system_block,
            "AGENTS:",
            agent_block,
            "SYMBOLS:",
            symbol_block,
            "CHAT_HISTORY:",
            history_block,
            f"CURRENT_QUERY: {user_prompt}"
        ]

        # Log diagnostic information
        log.debug(
            "context_manager.prompt_built",
            system_prompts=len(self.system_prompts),
            agent_characters=len(agent_block),
            symbol_characters=len(symbol_block),
            history_characters=len(history_block),
            total_characters=len(system_block) + len(agent_block) + len(symbol_block) + len(history_block)
        )

        prompt = "\n\n".join(sections)
        return prompt
