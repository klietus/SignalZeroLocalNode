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
from app.symbol_store import get_symbol, get_agent
from app.domain_types import AgentPersona, Symbol
from app.default_context_config import DEFAULT_AGENT_IDS, DEFAULT_SYMBOL_IDS


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

    default_agents = _load_default_agents()
    log.debug("inference.default_agents", default_agents=default_agents)
    context_agents: List[AgentPersona] = list(default_agents)
    agent_lookup: Dict[str, AgentPersona] = {agent.id: agent for agent in default_agents}

    default_symbols = _load_default_symbols()
    log.debug("inference.default_symbols", default_symbols=default_symbols)
    context_symbols: List[Symbol] = []
    symbol_lookup: Dict[str, Symbol] = {symbol.id: symbol for symbol in default_symbols}
    for sid, _ in nearest:
        symbol = get_symbol(sid)
        if symbol:
            context_symbols.append(symbol)
            symbol_lookup[symbol.id] = symbol
            log.debug("inference.symbol_context_added", symbol_id=symbol.id)

    chat_turns = chat_history.get_history(session_id)

    final_reply = None
    accumulated_history = []
    phase_responses: List[dict] = []

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
        for agent in context_agents:
            ctx.add_agent(agent)
        for symbol in default_symbols:
            ctx.add_symbol(symbol, relevance=2.0)
        for s in context_symbols:
            ctx.add_symbol(s)

        phase_prompt = ctx.build_prompt(user_query)
        log.debug("inference.phase_prompt", phase_prompt=phase_prompt)
        reply_text = model_call(phase_prompt)
        log.debug("inference.phase_reply", reply_text=reply_text)
        log.info(
            "inference.phase_intermediate",
            phase_id=phase_id,
            workflow=workflow,
            session_id=session_id,
            response=reply_text,
        )
        log.info(
            "inference.phase_completed",
            phase_id=phase_id,
            session_id=session_id,
            reply_length=len(reply_text),
        )

        phase_responses.append(
            {
                "phase_id": phase_id,
                "workflow": workflow,
                "response": reply_text,
            }
        )

        # Execute any emitted commands
        phase_commands = interpreter.run(reply_text)
        executed_commands.extend(phase_commands)
        log.debug(
            "inference.commands_executed",
            phase_id=phase_id,
            command_count=len(phase_commands),
        )

        for entry in phase_commands:
            if not isinstance(entry, dict):
                continue
            if entry.get("action") != "invoke_agent":
                continue
            result = entry.get("result")
            agent: AgentPersona | None = None
            if isinstance(result, AgentPersona):
                agent = result
            elif isinstance(result, dict) and result.get("id"):
                try:
                    agent = AgentPersona(**result)
                except Exception:  # pragma: no cover - validation safeguard
                    agent = None
            if not agent:
                continue
            if agent.id in agent_lookup:
                continue
            context_agents.append(agent)
            agent_lookup[agent.id] = agent
            log.info("inference.agent_appended", agent_id=agent.id)

        # Log output
        accumulated_history.append(("assistant", reply_text))
        command_notes = integrate_command_results(
            phase_commands, context_symbols, symbol_lookup
        )
        for note in command_notes:
            accumulated_history.append(("system", f"[command] {note}"))
        final_reply = reply_text

        log.info("inference.history_appended", session_id=session_id, turns=len(chat_turns))


    log.info(
        "inference.run_query.completed",
        session_id=session_id,
        commands=len(executed_commands),
        symbols=len(context_symbols),
    )
    
    chat_history.append_message(session_id, "query", user_query)
    chat_history.append_message(session_id, "assistant", final_reply)

    all_symbol_ids = [symbol.id for symbol in default_symbols]
    all_symbol_ids.extend(s.id for s in context_symbols)

    return {
        "reply": final_reply,
        "symbols_used": all_symbol_ids,
        "history_length": len(chat_turns) + len(accumulated_history),
        "commands": executed_commands,
        "intermediate_responses": phase_responses,
    }


def _load_default_agents() -> List[AgentPersona]:
    agents: List[AgentPersona] = []
    seen: set[str] = set()
    for agent_id in DEFAULT_AGENT_IDS:
        agent = get_agent(agent_id)
        if not agent:
            log.debug("inference.default_agent_missing", agent_id=agent_id)
            continue
        if agent.id in seen:
            continue
        agents.append(agent)
        seen.add(agent.id)
    return agents


def _load_default_symbols() -> List[Symbol]:
    symbols: List[Symbol] = []
    seen: set[str] = set()
    for symbol_id in DEFAULT_SYMBOL_IDS:
        symbol = get_symbol(symbol_id)
        if not symbol:
            log.debug("inference.default_symbol_missing", symbol_id=symbol_id)
            continue
        if symbol.id in seen:
            continue
        symbols.append(symbol)
        seen.add(symbol.id)
    return symbols
