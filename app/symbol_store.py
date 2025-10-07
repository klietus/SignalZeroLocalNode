# app/symbol_store.py

from typing import List, Dict, Optional
from app.types import Symbol, Facets
from pydantic import BaseModel
from app import embedding_index
import redis
import json
import os
import json
from pathlib import Path
from app.types import Symbol

# --------- Redis Setup ---------

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)

# --------- Redis Symbol Logic ---------

symbol_index: dict[str, Symbol] = {}

def load_symbol_store_if_empty(path="data/symbol_catalog.min.json"):

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

