"""Inference orchestration utilities."""

from pathlib import Path
from typing import Dict, List

import structlog

from app import embedding_index
from app.chat_history import ChatHistory
from app.command_interpreter import CommandInterpreter
from app.command_utils import integrate_command_results
from app.context_manager import ContextManager
from app.logging_config import configure_logging
from app.model_call import model_call
from app.symbol_store import get_symbol
from app.types import Symbol


configure_logging()
log = structlog.get_logger(__name__)


def load_prompt_phase(phase_id: str, workflow: str = "user") -> str:
    base = Path(f"data/prompts/{workflow}")
    path = base / f"{phase_id}.txt"
    if not path.exists():
        log.error("inference.prompt_missing", workflow=workflow, phase=phase_id)
        raise FileNotFoundError(f"Prompt phase not found: {path}")
    content = path.read_text().strip()
    log.debug(
        "inference.prompt_loaded",
        workflow=workflow,
        phase=phase_id,
        length=len(content),
    )
    return content

WORKFLOW_PHASES = [
    ("00-init", "user"),
    ("01-plan", "user"),
    ("02-expand", "user"),
    ("03-observe", "user"),
    ("04-reason", "user"),
    ("05-synthesize", "user"),
    ("06-refine", "user"),
    ("07-evaluate", "user"),
    ("08-log", "user")
]

def run_query(user_query: str, session_id: str, k: int = 5) -> dict:
    chat_history = ChatHistory()

    log.info(
        "inference.run_query.start",
        session_id=session_id,
        query_length=len(user_query),
        neighbours=k,
    )

    nearest = embedding_index.search(user_query, k)
    log.debug("inference.similarity_results", results=len(nearest))

    context_symbols: List[Symbol] = []
    symbol_lookup: Dict[str, Symbol] = {}
    for sid, _ in nearest:
        symbol = get_symbol(sid)
        if symbol:
            context_symbols.append(symbol)
            symbol_lookup[symbol.id] = symbol
            log.debug("inference.symbol_context_added", symbol_id=symbol.id)

    chat_turns = chat_history.get_history(session_id)
    chat_history.append_message(session_id, "user", user_query)
    log.info("inference.history_appended", session_id=session_id, turns=len(chat_turns))

    final_reply = None
    accumulated_history = []

    interpreter = CommandInterpreter()
    executed_commands = []
    handler_count = getattr(interpreter, "handler_count", None)
    log.debug("inference.interpreter_ready", handlers=handler_count)

    for phase_id, workflow in WORKFLOW_PHASES:
        ctx = ContextManager()
        ctx.add_system_prompt(load_prompt_phase("system_prompt", "shared"))
        ctx.add_system_prompt(load_prompt_phase("command_syntax", "shared"))
        ctx.add_system_prompt(load_prompt_phase("symbol_format", "shared"))
        ctx.add_system_prompt(load_prompt_phase(phase_id, workflow))

        # Inject recent messages and symbols
        for role, content in chat_turns + accumulated_history:
            ctx.add_history(role, content)
        for s in context_symbols:
            ctx.add_symbol(s)

        phase_prompt = ctx.build_prompt(user_query)
        reply_text = model_call(phase_prompt)
        log.info(
            "inference.phase_completed",
            phase_id=phase_id,
            session_id=session_id,
            reply_length=len(reply_text),
        )

        # Execute any emitted commands
        phase_commands = interpreter.run(reply_text)
        executed_commands.extend(phase_commands)
        log.debug(
            "inference.commands_executed",
            phase_id=phase_id,
            command_count=len(phase_commands),
        )

        # Log output
        accumulated_history.append(("assistant", reply_text))
        command_notes = integrate_command_results(
            phase_commands, context_symbols, symbol_lookup
        )
        for note in command_notes:
            accumulated_history.append(("system", f"[command] {note}"))
        final_reply = reply_text

    log.info(
        "inference.run_query.completed",
        session_id=session_id,
        commands=len(executed_commands),
        symbols=len(context_symbols),
    )

    chat_history.append_message(session_id, "assistant", final_reply)

    return {
        "reply": final_reply,
        "symbols_used": [s.id for s in context_symbols],
        "history_length": len(chat_turns) + len(accumulated_history),
        "commands": executed_commands,
    }

