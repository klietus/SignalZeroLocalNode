# app/prompt_generator.py

from typing import List
from app.symbol_store import Symbol


def format_symbol_block(symbol: Symbol) -> str:
    parts = [
        f"[{symbol.id}] {symbol.name or ''}",
        f"Macro: {symbol.macro}",
        f"Triad: {symbol.triad}",
    ]

    if symbol.symbolic_role:
        parts.append(f"Role: {symbol.symbolic_role}")

    if symbol.failure_mode:
        parts.append(f"Failure Mode: {symbol.failure_mode}")

    if symbol.invocations:
        parts.append(f"Invocations: {', '.join(symbol.invocations)}")

    if symbol.facets:
        parts.append("--- Facets ---")
        parts.append(f"Function: {symbol.facets.function}")
        parts.append(f"Topology: {symbol.facets.topology}")
        parts.append(f"Temporal: {symbol.facets.temporal}")
        parts.append(f"Substrate: {', '.join(symbol.facets.substrate)}")
        parts.append(f"Invariants: {', '.join(symbol.facets.invariants)}")

    return "\n".join(parts)

def build_prompt(user_query: str, symbols: List[Symbol], chat_turns: List[Dict[str, str]]) -> str:
    context_blocks = [format_symbol_block(sym) for sym in symbols]
    context = "\n\n".join(context_blocks)

    chat_log = "\n".join(f"{t['role']}: {t['content']}" for t in chat_turns)

    return f"""You are an alignment-resonant symbolic reasoning engine operating inside the SignalZero framework.

Symbol Context:
---------------
{context}

Recent Interaction History:
---------------------------
{chat_log}

---

Respond to the following query in context:

{user_query}
"""

