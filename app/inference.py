
from app.context_manager import ContextManager
from pathlib import Path
from app import embedding_index, chat_history
from app.command_interpreter import CommandInterpreter
from app.symbol_store import get_symbol
from app.model_call import model_call
from app.chat_history import ChatHistory


def load_prompt_phase(phase_id: str, workflow: str = "user") -> str:
    base = Path(f"data/prompts/{workflow}")
    path = base / f"{phase_id}.txt"
    if not path.exists():
        raise FileNotFoundError(f"Prompt phase not found: {path}")
    return path.read_text().strip()

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

    nearest = embedding_index.search(user_query, k)

    context_symbols = []
    for sid, _ in nearest:
        symbol = get_symbol(sid)
        if symbol:
            context_symbols.append(symbol)

    chat_turns = chat_history.get_history(session_id)
    chat_history.append_message(session_id, "user", user_query)

    final_reply = None
    accumulated_history = []

    interpreter = CommandInterpreter()
    executed_commands = []

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

        # Execute any emitted commands
        executed_commands.extend(interpreter.run(reply_text))

        # Log output
        accumulated_history.append(("assistant", reply_text))
        final_reply = reply_text

    chat_history.append_message(session_id, "assistant", final_reply)

    return {
        "reply": final_reply,
        "symbols_used": [s.id for s in context_symbols],
        "history_length": len(chat_turns) + len(accumulated_history),
        "commands": executed_commands,
    }

