# app/agency_loop.py

"""Autonomous agency loop for self-directed planning and execution."""

import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

import structlog

from app.chat_history import ChatHistory
from app.command_interpreter import CommandInterpreter
from app.command_utils import integrate_command_results
from app.context_manager import ContextManager
from app.logging_config import configure_logging
from app.model_call import model_call
from app.symbol_store import get_symbols
from app.types import Symbol


configure_logging()
log = structlog.get_logger(__name__)


# ----- Configuration -----

SELF_PROMPT_DIR = Path("data/prompts/self")
SHARED_PROMPT_DIR = Path("data/prompts/shared")

SELF_SESSION_ID = os.getenv("AGENCY_SESSION_ID", "self")
SYMBOL_LIMIT = int(os.getenv("AGENCY_SYMBOL_LIMIT", "32"))
LOOP_INTERVAL = int(os.getenv("AGENCY_LOOP_INTERVAL", "300"))


def _load_prompt(path: Path) -> str:
    if not path.exists():
        log.error("agency_loop.prompt_missing", path=str(path))
        raise FileNotFoundError(f"Prompt not found: {path}")
    content = path.read_text(encoding="utf-8").strip()
    log.debug("agency_loop.prompt_loaded", path=str(path), length=len(content))
    return content


def _load_shared_prompts() -> List[str]:
    shared_files = [
        SHARED_PROMPT_DIR / "system_prompt.txt",
        SHARED_PROMPT_DIR / "command_syntax.txt",
        SHARED_PROMPT_DIR / "symbol_format.txt",
    ]
    return [_load_prompt(path) for path in shared_files]


def _load_self_phases() -> List[Tuple[str, str]]:
    phase_files = sorted(SELF_PROMPT_DIR.glob("*.txt"))
    if not phase_files:
        log.error("agency_loop.self_prompts_missing", directory=str(SELF_PROMPT_DIR))
        raise RuntimeError(
            "No self-agency prompt phases found in data/prompts/self."
        )
    phases = [(path.stem, _load_prompt(path)) for path in phase_files]
    log.info("agency_loop.self_prompts_loaded", count=len(phases))
    return phases


SHARED_PROMPTS: List[str] = _load_shared_prompts()
SELF_PHASES: List[Tuple[str, str]] = _load_self_phases()


def _build_context(
    base_history: Sequence[Tuple[str, str]],
    interim_history: Sequence[Tuple[str, str]],
    symbols: Iterable,
    phase_prompt: str,
) -> ContextManager:
    ctx = ContextManager()
    for shared_prompt in SHARED_PROMPTS:
        ctx.add_system_prompt(shared_prompt)
    ctx.add_system_prompt(phase_prompt)

    for role, content in list(base_history) + list(interim_history):
        ctx.add_history(role, content)

    for symbol in symbols:
        ctx.add_symbol(symbol)

    return ctx


def _run_phase(
    phase_id: str,
    phase_prompt: str,
    iteration: int,
    timestamp: str,
    base_history: Sequence[Tuple[str, str]],
    interim_history: Sequence[Tuple[str, str]],
    symbols: Sequence,
) -> str:
    ctx = _build_context(base_history, interim_history, symbols, phase_prompt)
    user_prompt = (
        f"Self-agency loop iteration {iteration} | phase {phase_id} | "
        f"timestamp {timestamp}. Execute according to the active mode instructions "
        "and provide structured output."
    )
    prompt_text = ctx.build_prompt(user_prompt)
    log.debug(
        "agency_loop.phase_invocation",
        phase_id=phase_id,
        iteration=iteration,
        timestamp=timestamp,
        base_history=len(base_history),
        interim_history=len(interim_history),
        symbol_count=len(list(symbols)),
    )
    return model_call(prompt_text)


def run_agency_loop() -> None:
    chat_history = ChatHistory()
    iteration = 0

    while True:
        iteration += 1
        timestamp = datetime.now(tz=timezone.utc).isoformat()
        log.info("agency_loop.iteration_start", iteration=iteration, timestamp=timestamp)

        try:
            retrieved_symbols = get_symbols(
                domain=None, tag=None, start=0, limit=SYMBOL_LIMIT
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            log.warning(
                "agency_loop.symbol_retrieval_failed",
                iteration=iteration,
                error=str(exc),
            )
            retrieved_symbols = []

        context_symbols: List[Symbol] = []
        symbol_lookup: Dict[str, Symbol] = {}
        for symbol in retrieved_symbols:
            if not getattr(symbol, "id", None):
                continue
            if symbol.id in symbol_lookup:
                continue
            context_symbols.append(symbol)
            symbol_lookup[symbol.id] = symbol

        persistent_history = chat_history.get_history(SELF_SESSION_ID)
        iteration_history: List[Tuple[str, str]] = []

        chat_history.append_message(
            SELF_SESSION_ID,
            "system",
            f"[iteration {iteration}] started at {timestamp}",
        )

        interpreter = CommandInterpreter()
        log.debug(
            "agency_loop.interpreter_created",
            handler_count=interpreter.handler_count,
        )

        for phase_id, phase_prompt in SELF_PHASES:
            phase_start = datetime.now(tz=timezone.utc).isoformat()
            log.info(
                "agency_loop.phase_start",
                phase_id=phase_id,
                phase_start=phase_start,
                iteration=iteration,
                prior_turns=len(persistent_history) + len(iteration_history),
            )

            try:
                reply = _run_phase(
                    phase_id,
                    phase_prompt,
                    iteration,
                    timestamp,
                    persistent_history,
                    iteration_history,
                    context_symbols,
                )
            except Exception as exc:  # pragma: no cover - defensive logging
                error_ts = datetime.now(tz=timezone.utc).isoformat()
                log.error(
                    "agency_loop.phase_failed",
                    phase_id=phase_id,
                    iteration=iteration,
                    error=str(exc),
                    timestamp=error_ts,
                )
                chat_history.append_message(
                    SELF_SESSION_ID,
                    "system",
                    f"[{error_ts}] Phase {phase_id} failed: {exc}",
                )
                break

            iteration_history.append(("assistant", reply))
            chat_history.append_message(
                SELF_SESSION_ID, "assistant", f"[{phase_id}] {reply}"
            )

            phase_commands = interpreter.run(reply)
            command_notes = integrate_command_results(
                phase_commands, context_symbols, symbol_lookup
            )
            for note in command_notes:
                formatted = f"[command][{phase_id}] {note}"
                iteration_history.append(("system", formatted))
                chat_history.append_message(SELF_SESSION_ID, "system", formatted)
            log.debug(
                "agency_loop.phase_complete",
                phase_id=phase_id,
                iteration=iteration,
                commands=len(phase_commands),
                command_notes=len(command_notes),
            )

        iteration_end = datetime.now(tz=timezone.utc).isoformat()
        log.info(
            "agency_loop.iteration_complete",
            iteration=iteration,
            timestamp=iteration_end,
            history_entries=len(iteration_history),
        )

        time.sleep(LOOP_INTERVAL)


if __name__ == "__main__":
    run_agency_loop()

