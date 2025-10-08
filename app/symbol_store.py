# app/symbol_store.py

from typing import Dict, Iterable, List, Optional, Union

import json
import os
from pathlib import Path

import redis
import structlog

from app import embedding_index
from app.logging_config import configure_logging
from app.types import AgentPersona, KitDefinition, Symbol


configure_logging()
log = structlog.get_logger(__name__)

# --------- Redis Setup ---------

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)

# --------- Redis Symbol Logic ---------

symbol_index: dict[str, Symbol] = {}
kits_index: Dict[str, KitDefinition] = {}
agents_index: Dict[str, AgentPersona] = {}

SYMBOL_KEY_PREFIX = "symbol:"

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
DEFAULT_SYMBOL_CATALOG = DATA_DIR / "symbol_catalog.min.json"
DEFAULT_AGENTS_PATH = DATA_DIR / "agents.json"
DEFAULT_KITS_PATH = DATA_DIR / "kits.min.json"


def _key(symbol_id: str) -> str:
    return f"{SYMBOL_KEY_PREFIX}{symbol_id}"


def _persist_symbol(symbol: Symbol) -> None:
    """Store a symbol in Redis and update auxiliary indexes."""

    r.set(_key(symbol.id), symbol.model_dump_json())
    embedding_index.add_symbol(symbol)
    if symbol.symbol_domain:
        r.sadd("domains", symbol.symbol_domain)


def _resolve_path(path: Optional[Union[str, Path]], default: Path) -> Path:
    if path is None:
        return default
    return Path(path)


def load_agents(path: Optional[Union[str, Path]] = None) -> int:
    agents_index.clear()
    file_path = _resolve_path(path, DEFAULT_AGENTS_PATH)
    if not file_path.exists():
        log.warning("symbol_store.agents_file_missing", path=str(file_path))
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
            log.error(
                "symbol_store.agent_load_failed",
                payload=persona,
                error=str(exc),
            )

    log.info("symbol_store.agents_loaded", count=count)

    return count


def load_kits(path: Optional[Union[str, Path]] = None) -> int:
    kits_index.clear()
    file_path = _resolve_path(path, DEFAULT_KITS_PATH)
    if not file_path.exists():
        log.warning("symbol_store.kits_file_missing", path=str(file_path))
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
            log.error(
                "symbol_store.kit_load_failed",
                payload=item,
                error=str(exc),
            )

    log.info("symbol_store.kits_loaded", count=count)
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
        log.debug("symbol_store.kit_missing", kit_id=kit_id)
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

def _existing_symbol_ids() -> set[str]:
    """Return the set of symbol identifiers already persisted in Redis."""

    existing: set[str] = set()

    def _record(raw_key):
        key = raw_key.decode("utf-8") if isinstance(raw_key, bytes) else raw_key
        if key.startswith(SYMBOL_KEY_PREFIX):
            existing.add(key[len(SYMBOL_KEY_PREFIX) :])

    try:
        iterator = getattr(r, "scan_iter")
    except AttributeError:
        for key in r.keys(f"{SYMBOL_KEY_PREFIX}*"):
            _record(key)
        return existing

    try:
        for key in iterator(match=f"{SYMBOL_KEY_PREFIX}*", count=100):
            _record(key)
    except TypeError:  # pragma: no cover - some clients ignore count kwarg
        for key in iterator(f"{SYMBOL_KEY_PREFIX}*"):
            _record(key)

    return existing


def load_symbol_store_if_empty(path: Optional[Union[str, Path]] = None):

    file_path = _resolve_path(path, DEFAULT_SYMBOL_CATALOG)

    log.info("symbol_store.initialise_if_empty", path=str(file_path))

    existing_ids = _existing_symbol_ids()
    if existing_ids:
        log.info(
            "symbol_store.initialise_existing_symbols", existing_count=len(existing_ids)
        )

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    loaded = 0
    skipped = 0
    for s in data:
        try:
            symbol = Symbol(**s)
            if symbol.id in existing_ids:
                skipped += 1
                continue
            _persist_symbol(symbol)
            existing_ids.add(symbol.id)
            loaded += 1
        except Exception as e:
            log.error(
                "symbol_store.symbol_load_failed",
                symbol_id=s.get("id", "[unknown]"),
                error=str(e),
            )

    log.info("symbol_store.symbols_loaded", count=loaded, skipped=skipped)
    load_agents()
    load_kits()

def get_symbol(symbol_id: str) -> Optional[Symbol]:
    raw = r.get(_key(symbol_id))
    if not raw:
        log.debug("symbol_store.symbol_missing", symbol_id=symbol_id)
    return Symbol.model_validate_json(raw) if raw else None


def put_symbol(symbol_id: str, symbol: Symbol) -> str:
    r.set(_key(symbol_id), symbol.model_dump_json())
    embedding_index.add_symbol(symbol)
    if symbol.symbol_domain:
        r.sadd("domains", symbol.symbol_domain)
    log.info("symbol_store.symbol_stored", symbol_id=symbol_id)
    return "stored"


def delete_symbol(symbol_id: str) -> bool:
    removed = r.delete(_key(symbol_id))
    if removed:
        try:
            embedding_index.build_index()
            log.info("symbol_store.symbol_deleted", symbol_id=symbol_id)
        except Exception as exc:  # pragma: no cover - rebuild failures are logged
            log.error(
                "symbol_store.index_rebuild_failed",
                symbol_id=symbol_id,
                error=str(exc),
            )
    else:
        log.debug("symbol_store.delete_noop", symbol_id=symbol_id)
    return bool(removed)


def put_symbols_bulk(symbols: List[Symbol]) -> str:
    pipe = r.pipeline()
    for s in symbols:
        pipe.set(_key(s.id), s.model_dump_json())
        embedding_index.add_symbol(s)
        if s.symbol_domain:
            pipe.sadd("domains", s.symbol_domain)
    pipe.execute()
    log.info("symbol_store.bulk_stored", count=len(symbols))
    return "bulk_stored"


def get_symbols(domain: Optional[str], tag: Optional[str], start: int, limit: int) -> List[Symbol]:
    keys = r.keys(f"{SYMBOL_KEY_PREFIX}*")
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

    sliced = results[start:start + limit]
    log.debug(
        "symbol_store.symbols_fetched",
        total=len(results),
        returned=len(sliced),
        domain=domain,
        tag=tag,
    )
    return sliced


def get_domains() -> List[str]:
    domains = list(r.smembers("domains"))
    log.debug("symbol_store.domains_fetched", count=len(domains))
    return domains


def get_symbols_by_ids(symbol_ids: Iterable[str]) -> List[Symbol]:
    ids: List[str] = [symbol_id for symbol_id in symbol_ids if isinstance(symbol_id, str)]
    if not ids:
        log.debug("symbol_store.bulk_fetch_empty")
        return []

    keys = [_key(symbol_id) for symbol_id in ids]
    raw_values = r.mget(keys)

    symbols: List[Symbol] = []
    for symbol_id, raw in zip(ids, raw_values):
        if not raw:
            log.debug("symbol_store.symbol_missing_bulk", symbol_id=symbol_id)
            continue
        try:
            symbols.append(Symbol.model_validate_json(raw))
        except Exception as exc:  # pragma: no cover - validation errors logged
            log.error(
                "symbol_store.symbol_decode_failed",
                symbol_id=symbol_id,
                error=str(exc),
            )
    log.debug("symbol_store.bulk_fetch_completed", requested=len(ids), returned=len(symbols))
    return symbols

