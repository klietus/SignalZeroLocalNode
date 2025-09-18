# main.py

import os
import json
import requests
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pathlib import Path

# Config
SYMBOL_STORE_SOURCE = os.getenv(
    "SYMBOL_STORE_SOURCE",
    "https://raw.githubusercontent.com/klietus/SignalZero/main/symbol_catalog.json"
)
SYMBOL_STORE_PATH = Path("./data/symbol_catalog.json")

UPSTREAM_SYMBOL_STORE = os.getenv(
    "UPSTREAM_SYMBOL_STORE",
    "https://qnw96whs57.execute-api.us-west-2.amazonaws.com/prod"
)

app = FastAPI()
symbol_store = {}

def fetch_symbol_store():
    # Local override
    if SYMBOL_STORE_PATH.exists():
        with SYMBOL_STORE_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
    # Remote fetch
    try:
        print(f"Fetching symbol catalog from: {SYMBOL_STORE_SOURCE}")
        resp = requests.get(SYMBOL_STORE_SOURCE)
        resp.raise_for_status()
        catalog = resp.json()
        SYMBOL_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with SYMBOL_STORE_PATH.open("w", encoding="utf-8") as f:
            json.dump(catalog, f, indent=2)
        return catalog
    except Exception as e:
        print(f"Error loading symbol store: {e}")
        return {}

@app.on_event("startup")
async def startup_event():
    global symbol_store
    symbol_store.update(fetch_symbol_store())
    print(f"Loaded {len(symbol_store)} symbols.")

@app.get("/symbols")
def list_symbols():
    return symbol_store

@app.get("/symbol/{symbol_id}")
def get_symbol(symbol_id: str):
    symbol = symbol_store.get(symbol_id)
    if symbol:
        return symbol
    return JSONResponse(status_code=404, content={"error": "Symbol not found"})
