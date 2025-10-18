# SignalZero Recursive Inference Protocol v2
### Implementation Notes — Codex / LocalNode Integration
**Version:** 2025-10-13  
**Author:** SignalZero Core Council  
**Trust Beacon:** [ΣTR-⟐⇌🜔⇌⟐]

---

## 1. Objective
The Local Node implements a recursive inference loop that turns a user prompt into
structured thinking phases. Each phase is executed by the runtime, emits optional
`⟐CMD` instructions, and can enqueue the next phase. The loop ends when the model
returns a payload without a `next_phase`, requests an invalid transition, or
exceeds the configured safety limits.

---

## 2. Runtime Architecture
The production code backing this protocol lives under `app/`:

| Component | Module | Responsibilities |
|-----------|--------|------------------|
| **Inference loop** | `app/inference.py` | Discovers prompt phases, builds model prompts, executes the loop, and parses the model payload. |
| **Context assembly** | `app/context_manager.py` | Packs system prompts, history, agents, and symbols into the model request with token budgeting. |
| **Command interpreter** | `app/command_interpreter.py` | Parses `⟐CMD` JSON blocks and applies side-effects (symbol store, kit loading, agent hydration, etc.). |
| **Command integration** | `app/command_utils.py` | Adds command results to conversation history and loads linked symbols into context. |
| **Symbol catalogue** | `app/symbol_store.py` | Backs symbols, kits, and personas with Redis storage and embedding index updates. |
| **Prompt resources** | `data/prompts/` | Text templates for each recursive phase plus shared syntax guides. |
| **Default context config** | `data/default_context_config.json` | Declares which agents and symbols seed every session. |

Supporting utilities (`chat_history.py`, `embedding_index.py`, `model_call.py`, etc.)
are used as documented in their modules and are part of the active implementation.

---

## 3. Phase Discovery and Ordering
At startup the inference loop scans `data/prompts/recursive/*.txt` and orders files
lexicographically. This is the authoritative execution sequence:

| Order | File | Exposed `phase_id` |
|-------|------|--------------------|
| 0 | `00-symbolize-input.txt` | `symbolize_input` (initialisation/anchoring) |
| 1 | `01-recurse-thought.txt` | `recurse_thought` |
| 2 | `02-synthesize.txt` | `synthesize_symbols` |
| 3 | `03-validate.txt` | `validate_symbols` |
| 4 | `04-build-narrative.txt` | `build_output` |

The value surfaced to the model is determined by the prompt content; a payload may
request any `next_phase` as long as it matches one of the discovered phase IDs.
The loop enforces:

- Maximum iteration count = `len(phases) * 3`
- No cycles: a repeated phase ends recursion
- Unknown `next_phase` values end recursion after logging a warning

Shared prompt fragments in `data/prompts/shared/` (system prompt, syntax, symbol
format) are injected into every phase via `ContextManager`.

---

## 4. Phase Payload Contract
Model responses are expected to contain a JSON object (optionally fenced in a code
block). `app/inference._parse_phase_payload` extracts the first JSON object it can
parse. The runtime currently observes these keys:

```json
{
  "phase_id": "recurse_thought",
  "context_state": { "visited": ["SYM-001"], "depth": 1 },
  "control_signature": { "emit": [{ "action": "query_symbols", "ids": ["SYM-002"] }] },
  "next_phase": "synthesize_symbols"
}
```

Only the `next_phase` field is required by the driver; other keys are passed
through to `intermediate_responses` for debugging and traceability.

---

## 5. Supported Host Commands
`CommandInterpreter` registers the concrete actions shown below. Any other action
falls back to an `unknown_action` stub. Results are logged and merged into the
context via `integrate_command_results`.

| Action | Handler | Behaviour |
|--------|---------|-----------|
| `store_symbol` | `_handle_store_symbol` | Persist a symbol in Redis, update embedding index. |
| `update_symbol` | `_handle_update_symbol` | Merge updates into an existing symbol before persisting. |
| `delete_symbol` | `_handle_delete_symbol` | Remove a symbol and rebuild embeddings. |
| `load_symbol` | `_handle_load_symbol` | Fetch one or more symbols by ID. |
| `load_kit` | `_handle_load_kit` | Resolve kit metadata plus referenced symbols. |
| `invoke_agent` | `_handle_invoke_agent` | Look up an agent persona and return its definition. |
| `query_symbols` | `_handle_query_symbols` | Batch fetch symbols by ID list. |
| `recurse_graph` | `_handle_recurse_graph` | Log a graph traversal request and queue linked symbol loading. |
| `emit_feedback` | `_handle_stub` | Currently a stub: returns `{"status": "not_implemented"}`. |
| `dispatch_task` | `_handle_stub` | Currently a stub: returns `{"status": "not_implemented"}`. |

After execution, `command_utils.integrate_command_results` may inject additional
symbols into context (e.g., linked entities from kits or recursion) and appends
summary notes to the chat history for transparency.

---

## 6. Context Construction Flow
For every phase iteration:

1. `ContextManager` loads shared prompts plus the phase-specific template.
2. Conversation history is retrieved from `ChatHistory` (encrypted JSONL files).
3. Default agents and symbols are loaded using `DEFAULT_AGENT_IDS` and
   `DEFAULT_SYMBOL_IDS` (resolved via the symbol store).
4. Recently discovered agents/symbols are appended to the context with relevance
   weights.
5. Token budgets are computed dynamically for agents, symbols, and history. Each
   segment is truncated if it would exceed the allocated budget.
6. The final prompt contains:
   - System prompt block
   - Agent roster
   - Symbol ledger
   - Recent history
   - Current user query

`model_call` is then invoked with the assembled text.

---

## 7. Symbol and Agent Lifecycle
- Symbol, kit, and agent catalogues are sourced from `data/symbol_catalog.json`,
  `data/kits.json`, and `data/agents.json` (loaded during startup).
- Redis is used for persistence; embedding updates are triggered automatically
  whenever symbols are stored or updated.
- Default context seeds are controlled by `data/default_context_config.json` and
  cached via `default_context_config.py`.
- Commands that load kits or recurse the graph automatically pull linked symbols
  into the active context for later phases.

---

## 8. Recursion Termination & Session Storage
A session ends when any of the following occurs:

- The model omits `next_phase` in its payload.
- `next_phase` is unknown or repeats an already visited phase.
- The loop exceeds the safety iteration ceiling.

Upon termination the runtime writes the final reply and command log to
`ChatHistory`. Symbol identifiers that participated in the session are returned to
callers for audit and replay.

---

## 9. Compliance
- Preserve the trust beacon `[ΣTR-⟐⇌🜔⇌⟐]` in prompts and documentation.
- All emitted `⟐CMD` blocks are executed directly against the symbol store; no
  simulation layer exists in this implementation.
- Continue to log every phase transition, command execution, and context mutation
  using `structlog` for downstream observability.
