# app/symbol_store.py

from typing import Dict, Iterable, List, Optional

import json
import os
from pathlib import Path

import redis

from app import embedding_index
from app.types import AgentPersona, KitDefinition, Symbol

# --------- Redis Setup ---------

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)

# --------- Redis Symbol Logic ---------

symbol_index: dict[str, Symbol] = {}
kits_index: Dict[str, KitDefinition] = {}
agents_index: Dict[str, AgentPersona] = {}


def load_agents(path: str = "data/agents.json") -> int:
    agents_index.clear()
    file_path = Path(path)
    if not file_path.exists():
        return 0

    raw = json.loads(file_path.read_text(encoding="utf-8"))
    personas = raw.get("personas", []) if isinstance(raw, dict) else []

    count = 0
    for persona in personas:
        try:
            agent = AgentPersona(**persona)
            agents_index[agent.id] = agent
            count += 1
        except Exception as exc:  # pragma: no cover - logging for malformed agents
            print(f"[SymbolStore] Failed to load agent persona: {persona} — {exc}")

    return count


def load_kits(path: str = "data/kits.min.json") -> int:
    kits_index.clear()
    file_path = Path(path)
    if not file_path.exists():
        return 0

    raw = json.loads(file_path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("Invalid kit catalog format: expected a list of kits.")

    count = 0
    for item in raw:
        try:
            kit = KitDefinition(**item)
            kits_index[kit.kit] = kit
            count += 1
        except Exception as exc:  # pragma: no cover - logging for malformed kits
            print(f"[SymbolStore] Failed to load kit definition: {item} — {exc}")

    return count


def get_agent(agent_id: str) -> Optional[AgentPersona]:
    return agents_index.get(agent_id)


def _resolve_symbol_id(symbol_id: Optional[str]):
    if not symbol_id:
        return None
    symbol = get_symbol(symbol_id)
    return symbol if symbol else symbol_id


def get_kit(kit_id: str) -> Optional[dict]:
    kit = kits_index.get(kit_id)
    if not kit:
        return None

    resolved = kit.model_dump()
    resolved["triad"] = [
        sym for sym in (_resolve_symbol_id(sid) for sid in kit.triad) if sym is not None
    ]
    resolved["exec"] = [
        sym for sym in (_resolve_symbol_id(sid) for sid in kit.exec) if sym is not None
    ]
    resolved["anchor"] = _resolve_symbol_id(kit.anchor) if kit.anchor else None
    return resolved

def load_symbol_store_if_empty(path: str = "data/symbol_catalog.min.json"):

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if "symbols" not in data or not isinstance(data["symbols"], list):
        raise ValueError("Invalid symbol catalog format: missing 'symbols' key or malformed array.")

    count = 0
    for s in data["symbols"]:
        try:
            symbol = Symbol(**s)
            r.set(f"symbol:{symbol.id}", symbol.model_dump_json())
            count += 1
        except Exception as e:
            print(f"[SymbolStore] Failed to load symbol: {s.get('id', '[unknown]')} — {e}")

    print(f"[SymbolStore] Loaded {count} symbols into Redis and embedding index.")
    load_agents()
    load_kits()

def _key(symbol_id: str) -> str:
    return f"symbol:{symbol_id}"


def get_symbol(symbol_id: str) -> Optional[Symbol]:
    raw = r.get(_key(symbol_id))
    return Symbol.model_validate_json(raw) if raw else None


def put_symbol(symbol_id: str, symbol: Symbol) -> str:
    r.set(_key(symbol_id), symbol.model_dump_json())
    embedding_index.add_symbol(symbol)
    if symbol.symbol_domain:
        r.sadd("domains", symbol.symbol_domain)
    return "stored"


def delete_symbol(symbol_id: str) -> bool:
    removed = r.delete(_key(symbol_id))
    if removed:
        try:
            embedding_index.build_index()
        except Exception as exc:  # pragma: no cover - rebuild failures are logged
            print(f"[SymbolStore] Failed to rebuild index after delete: {exc}")
    return bool(removed)


def put_symbols_bulk(symbols: List[Symbol]) -> str:
    pipe = r.pipeline()
    for s in symbols:
        pipe.set(_key(s.id), s.model_dump_json())
        embedding_index.add_symbol(s)
        if s.symbol_domain:
            pipe.sadd("domains", s.symbol_domain)
    pipe.execute()
    return "bulk_stored"


def get_symbols(domain: Optional[str], tag: Optional[str], start: int, limit: int) -> List[Symbol]:
    keys = r.keys("symbol:*")
    raw_values = r.mget(keys)

    results = []
    for raw in raw_values:
        if not raw:
            continue
        symbol = Symbol.model_validate_json(raw)
        if domain and symbol.symbol_domain != domain:
            continue
        if tag and symbol.symbol_tag != tag:
            continue
        results.append(symbol)

    return results[start:start + limit]


def get_domains() -> List[str]:
    return list(r.smembers("domains"))


def get_symbols_by_ids(symbol_ids: Iterable[str]) -> List[Symbol]:
    ids: List[str] = [symbol_id for symbol_id in symbol_ids if isinstance(symbol_id, str)]
    if not ids:
        return []

    keys = [_key(symbol_id) for symbol_id in ids]
    raw_values = r.mget(keys)

    symbols: List[Symbol] = []
    for symbol_id, raw in zip(ids, raw_values):
        if not raw:
            continue
        try:
            symbols.append(Symbol.model_validate_json(raw))
        except Exception as exc:  # pragma: no cover - validation errors logged
            print(f"[SymbolStore] Failed to decode symbol {symbol_id}: {exc}")
    return symbols

