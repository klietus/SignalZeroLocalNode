# app/agency_loop.py

"""Autonomous agency loop for self-directed planning and execution."""

import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

from app.chat_history import ChatHistory
from app.context_manager import ContextManager
from app.model_call import model_call
from app.symbol_store import get_symbols


# ----- Configuration -----

SELF_PROMPT_DIR = Path("data/prompts/self")
SHARED_PROMPT_DIR = Path("data/prompts/shared")

SELF_SESSION_ID = os.getenv("AGENCY_SESSION_ID", "self")
SYMBOL_LIMIT = int(os.getenv("AGENCY_SYMBOL_LIMIT", "32"))
LOOP_INTERVAL = int(os.getenv("AGENCY_LOOP_INTERVAL", "300"))


def _load_prompt(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Prompt not found: {path}")
    return path.read_text(encoding="utf-8").strip()


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
        raise RuntimeError(
            "No self-agency prompt phases found in data/prompts/self."
        )
    return [(path.stem, _load_prompt(path)) for path in phase_files]


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
    return model_call(prompt_text)


def run_agency_loop() -> None:
    chat_history = ChatHistory()
    iteration = 0

    while True:
        iteration += 1
        timestamp = datetime.now(tz=timezone.utc).isoformat()
        print(f"[{timestamp}] 🌀 SELF AGENCY LOOP: iteration {iteration} starting...")

        try:
            symbols = get_symbols(domain=None, tag=None, start=0, limit=SYMBOL_LIMIT)
        except Exception as exc:  # pragma: no cover - defensive logging
            print(f"[{timestamp}] ⚠️ Failed to retrieve symbols: {exc}")
            symbols = []

        persistent_history = chat_history.get_history(SELF_SESSION_ID)
        iteration_history: List[Tuple[str, str]] = []

        chat_history.append_message(
            SELF_SESSION_ID,
            "system",
            f"[iteration {iteration}] started at {timestamp}",
        )

        for phase_id, phase_prompt in SELF_PHASES:
            phase_start = datetime.now(tz=timezone.utc).isoformat()
            print(
                f"[{phase_start}] ➡️ SELF phase {phase_id}: invoking model with"
                f" {len(persistent_history) + len(iteration_history)} prior turns"
            )

            try:
                reply = _run_phase(
                    phase_id,
                    phase_prompt,
                    iteration,
                    timestamp,
                    persistent_history,
                    iteration_history,
                    symbols,
                )
            except Exception as exc:  # pragma: no cover - defensive logging
                error_ts = datetime.now(tz=timezone.utc).isoformat()
                error_msg = f"[{error_ts}] ❌ Phase {phase_id} failed: {exc}"
                print(error_msg)
                chat_history.append_message(SELF_SESSION_ID, "system", error_msg)
                break

            iteration_history.append(("assistant", reply))
            chat_history.append_message(
                SELF_SESSION_ID, "assistant", f"[{phase_id}] {reply}"
            )

        iteration_end = datetime.now(tz=timezone.utc).isoformat()
        print(
            f"[{iteration_end}] ✅ SELF AGENCY LOOP: iteration {iteration} complete."
        )

        time.sleep(LOOP_INTERVAL)


if __name__ == "__main__":
    run_agency_loop()

