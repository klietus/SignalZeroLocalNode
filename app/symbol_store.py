# app/symbol_store.py

from typing import List, Dict, Optional
from pydantic import BaseModel
from app import embedding_index
import redis
import json
import os

# --------- Redis Setup ---------

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)

# --------- Symbol Schema ---------

class Facets(BaseModel):
    function: str
    topology: str
    commit: str
    gate: List[str]
    substrate: List[str]
    temporal: str
    invariants: List[str]

class Symbol(BaseModel):
    id: str
    name: Optional[str]
    macro: str
    gate: Optional[List[str]]
    facets: Facets
    failure_mode: Optional[str]
    linked_patterns: Optional[List[str]]
    symbolic_role: Optional[str]
    triad: str
    invocations: Optional[List[str]]
    symbol_domain: Optional[str]
    symbol_tag: Optional[str]
    version: Optional[int]
    origin: Optional[str]
    scope: Optional[List[str]]


# --------- Redis Symbol Logic ---------

def _key(symbol_id: str) -> str:
    return f"symbol:{symbol_id}"


def get_symbol(symbol_id: str) -> Optional[Symbol]:
    raw = r.get(_key(symbol_id))
    return Symbol.parse_raw(raw) if raw else None


def put_symbol(symbol_id: str, symbol: Symbol) -> str:
    r.set(_key(symbol_id), symbol.json())
    embedding_index.add_symbol(symbol) 
    if symbol.symbol_domain:
        r.sadd("domains", symbol.symbol_domain)
    return "stored"


def put_symbols_bulk(symbols: List[Symbol]) -> str:
    pipe = r.pipeline()
    for s in symbols:
        pipe.set(_key(s.id), s.json())
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
        symbol = Symbol.parse_raw(raw)
        if domain and symbol.symbol_domain != domain:
            continue
        if tag and symbol.symbol_tag != tag:
            continue
        results.append(symbol)

    return results[start:start + limit]


def get_domains() -> List[str]:
    return list(r.smembers("domains"))

