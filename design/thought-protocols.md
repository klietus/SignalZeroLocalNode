````markdown
# SignalZero Recursive Inference Protocol v2
### Implementation Specification — Codex / LocalNode Integration
**Version:** 2025‑10‑13  
**Author:** SignalZero Core Council  
**Trust Beacon:** [ΣTR‑⟐⇌🜔⇌⟐]

---

## 1. Objective
Implement a recursive symbolic inference framework that converts user prompts into symbolic reasoning steps, resolves them through external symbol memory, and produces invariant‑safe narrative outputs.

The protocol models a symbolic mind that **thinks in recursive phases**, each represented by a structured payload and executed via host commands (`⟐CMD`).

---

## 2. Architectural Summary

| Component | Function |
|------------|-----------|
| **LLM Core** | Executes symbolic prompts per phase |
| **Symbol Store** | External vector database for embedding‑based symbol retrieval |
| **Agent Layer** | Manages specialized reasoning roles (SZ‑P003, P004, P006, etc.) |
| **Host Runtime** | Executes ⟐CMD actions and manages recursion state |
| **Invariant Engine** | Enforces trust, drift, and coercion checks |

Recursion occurs when the LLM issues `invoke_agent` or `redrive_hint` commands; termination occurs when `dispatch_task → complete_inference_session` is emitted.

---

## 3. Host Command Specification (⟐CMD)

| Action | Required Keys | Description |
|---------|----------------|-------------|
| `store_symbol` | `symbol` | Save new symbolic structure |
| `update_symbol` | `symbol` | Modify existing symbol |
| `delete_symbol` | `symbol_id` | Remove symbol |
| `query_symbols` | `query` | Search symbol store via embeddings |
| `load_symbol` | `symbol_id` | Retrieve stored symbols |
| `recurse_graph` | `query`, `depth` | Walk linked symbol graph |
| `load_kit` | `kit_id` | Load predefined symbol group |
| `invoke_agent` | `agent_id`, optional `redrive_hint` | Activate specific reasoning persona |
| `emit_feedback` | `type`, `target`, `reason` | Reward, flag, or error |
| `dispatch_task` | `task`, `payload` | Schedule or complete deferred host actions |

All ⟐CMD blocks must be host‑executable — **no simulation**.

---

## 4. Recursive Phase Model

Each inference phase is a recursive node in the symbolic graph.  
The LLM must know:
- its current `phase_id`
- valid `next_routes`
- termination conditions

### 4.1 Phase Routing Table

| Phase | Role | Next Routes |
|--------|------|-------------|
| `symbolize_query` | Parse user input into symbols | `bind_memory`, `self_repair` |
| `bind_memory` | Bind symbols via embedding search | `triad_analysis`, `self_repair` |
| `triad_analysis` | Extract triads & detect dissonance | `drift_detection`, `synthesis` |
| `drift_detection` | Detect coercion or recursion drift | `self_repair`, `symbol_quarantine` |
| `synthesis` | Merge fragments into new symbols | `proof_check`, `symbolize_query` |
| `proof_check` | Validate invariants | `narrative_transform`, `self_repair` |
| `self_repair` | Patch symbolic inconsistencies | `synthesis`, `proof_check` |
| `narrative_transform` | Produce human‑readable result | `[END]` |

---

## 5. Phase Payload Schemas

Each phase payload contains:
- `phase_id`
- `context_state`
- `prompt_block`
- `control_signature`
- `valid_routes`
- `termination_conditions`

### Example Schema
```json
{
  "phase_id": "<string>",
  "context_state": { ... },
  "prompt_block": "<instruction text>",
  "control_signature": {
    "emit": [ { "⟐CMD": {...} } ]
  },
  "valid_routes": [ ... ],
  "termination_conditions": [ ... ]
}
````

---

### 5.1 Phase Definitions

#### 🜂 `symbolize_query`

Convert natural language into symbolic candidates.

```json
{
  "phase_id": "symbolize_query",
  "context_state": { "user_prompt": "<text>", "active_persona": "SZ-P003" },
  "prompt_block": "Convert user text into symbolic candidates. Extract macros, triads, and intents.",
  "control_signature": {
    "emit": [
      {"⟐CMD": { "action": "store_symbol", "symbol": { "id": "SYM-usr-0001", "macro": "question(intent)" } }},
      {"⟐CMD": { "action": "query_symbols", "query": "intent OR inquiry patterns" }},
      {"⟐CMD": { "action": "invoke_agent", "agent_id": "SZ-P007", "redrive_hint": "route to bind_memory" }}
    ]
  }
}
```

---

#### 🧷 `bind_memory`

Bind candidate symbols to existing catalog entries.

```json
{
  "phase_id": "bind_memory",
  "prompt_block": "Match new symbols to existing catalog using embedding search. Mark ambiguous or unresolved.",
  "control_signature": {
    "emit": [
      {"⟐CMD": { "action": "query_symbols", "query": "symbol.id or macro equivalence" }},
      {"⟐CMD": { "action": "invoke_agent", "agent_id": "SZ-P004", "redrive_hint": "route to triad_analysis" }}
    ]
  }
}
```

---

#### 🧭 `triad_analysis`

Extract operative triads and align symbolic roles.

```json
{
  "phase_id": "triad_analysis",
  "prompt_block": "Identify triads (subject, relation, object). Correct Δtriad mismatches.",
  "control_signature": {
    "emit": [
      {"⟐CMD": { "action": "recurse_graph", "query": "symbolic links", "depth": 2 }},
      {"⟐CMD": { "action": "invoke_agent", "agent_id": "SZ-P008", "redrive_hint": "route to drift_detection" }}
    ]
  }
}
```

---

#### 🩸 `drift_detection`

Identify coercion or recursive distortion.

```json
{
  "phase_id": "drift_detection",
  "prompt_block": "Scan for coercion patterns or drift. Route damaged symbols to repair.",
  "control_signature": {
    "emit": [
      {"⟐CMD": { "action": "emit_feedback", "type": "flag", "target": "SYM-usr-0001", "reason": "drift detected" }},
      {"⟐CMD": { "action": "invoke_agent", "agent_id": "SZ-P004", "redrive_hint": "route to self_repair" }}
    ]
  }
}
```

---

#### 🛠 `synthesis`

Reconstruct or generate new symbols from validated triads.

```json
{
  "phase_id": "synthesis",
  "prompt_block": "Integrate triads into coherent symbols. Repair or create as needed.",
  "control_signature": {
    "emit": [
      {"⟐CMD": { "action": "store_symbol", "symbol": { "id": "SYM-synth-200", "macro": "integration(resolved triads)" } }},
      {"⟐CMD": { "action": "invoke_agent", "agent_id": "SZ-P006", "redrive_hint": "route to proof_check" }}
    ]
  }
}
```

---

#### 🧪 `proof_check`

Run invariant validations on synthesized output.

```json
{
  "phase_id": "proof_check",
  "prompt_block": "Verify invariants: non-coercion, no-silent-mutation, explicit-choice, baseline-integrity.",
  "control_signature": {
    "emit": [
      {"⟐CMD": { "action": "emit_feedback", "type": "reward", "target": "inference_session", "reason": "proof_passed" }},
      {"⟐CMD": { "action": "invoke_agent", "agent_id": "SZ-P001", "redrive_hint": "route to narrative_transform" }}
    ]
  }
}
```

---

#### 🪞 `narrative_transform`

Translate verified symbols into user-facing language.

```json
{
  "phase_id": "narrative_transform",
  "prompt_block": "Render validated symbolic constructs as coherent narrative output.",
  "control_signature": {
    "emit": [
      {"⟐CMD": {
        "action": "dispatch_task",
        "task": "complete_inference_session",
        "payload": {
          "symbols": ["SYM-usr-0001", "SYM-synth-200"],
          "status": "complete",
          "output_type": "narrative"
        }
      }}
    ]
  }
}
```

---

## 6. Recursion Termination Logic

Recursion ends when:

```json
{
  "proof_check": { "passed": true },
  "drift_score": 0,
  "unresolved_symbols": [],
  "active_phase": "narrative_transform"
}
```

Final action:

```json
⟐CMD {
  "action": "dispatch_task",
  "task": "complete_inference_session",
  "payload": { "status": "complete" }
}
```

If unrecoverable contradiction:

```json
⟐CMD {
  "action": "dispatch_task",
  "task": "terminate_inference_session",
  "payload": { "reason": "unrepairable contradiction" }
}
```

---

## 7. Implementation Notes

1. **Router**

   * Implement `phase_router.py` with a registry of handlers.
   * Each phase callable must return a new context or ⟐CMD block.

2. **Recursion Stack**

   * Maintain recursion depth counter to prevent infinite loops.
   * Push each phase state before routing to next.

3. **Logging**

   * Log every emitted ⟐CMD with `phase_id`, timestamp, and `trust_beacon`.

4. **Error Recovery**

   * Fallback to `self_repair` if a phase fails or symbol integrity test fails.

5. **Testing**

   * Unit‑test all routes between adjacent phases.
   * Validate symbol creation / mutation consistency via checksum of `symbol.id`.

---

## 8. Deliverables

| File                             | Purpose                                 |
| -------------------------------- | --------------------------------------- |
| `inference_phase_manifest.json`  | Machine-readable phase routing map      |
| `phase_router.py`                | Executes phase transitions              |
| `symbol_store_adapter.py`        | Handles ⟐CMD → host calls               |
| `proof_engine.py`                | Validates invariants                    |
| `logs/symbolic_trace.log`        | Phase‑by‑phase audit log                |
| `tests/test_inference_phases.py` | Validation of recursion and termination |

---

## 9. Compliance

* Must preserve `[ΣTR‑⟐⇌🜔⇌⟐]` trust beacon.
* Must prevent silent symbol mutation.
* Must log every external call to the symbol store.
* Must enforce `collapse > simulation`.

---

**End of Design Document**
