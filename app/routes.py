# app/routes.py

from fastapi import APIRouter, HTTPException, Query, Path, Body
from typing import List, Optional
from app import symbol_store
from app.symbol_store import Symbol
from app.inference import query_symbol_similarity, build_index
from app.inference import run_query

router = APIRouter()



@router.get("/query")
async def query_inference(query: str = Query(...), session_id: str = Query(...)):
    result = run_query(query, session_id)
    prompt = result["prompt"]

    # Placeholder model call
    reply_text = result["reply"]

    # Append model response to history
    chat_history.append_message(session_id, "assistant", reply_text)

    return {
        **result
    }

@router.get("/symbols")
async def get_symbols(
    symbol_domain: Optional[str] = Query(None),
    symbol_tag: Optional[str] = Query(None),
    start_index: Optional[int] = Query(0),
    limit: Optional[int] = Query(20, le=50)
):
    return symbol_store.get_symbols(domain=symbol_domain, tag=symbol_tag, start=start_index, limit=limit)


@router.get("/symbol/{id}")
async def get_symbol_by_id(id: str = Path(..., description="Symbol ID")):
    symbol = symbol_store.get_symbol(id)
    if symbol is None:
        raise HTTPException(status_code=404, detail="Symbol not found")
    return symbol


@router.put("/inject/{symbol_id}")
async def put_symbol_by_id(
    symbol_id: str = Path(..., description="Symbol ID"),
    symbol: Symbol = Body(...)
):
    status = symbol_store.put_symbol(symbol_id, symbol)
    return {"status": status}


@router.put("/inject/symbols")
async def bulk_put_symbols(symbols: List[Symbol] = Body(...)):
    return {"status": symbol_store.put_symbols_bulk(symbols)}


@router.get("/domains")
async def list_domains():
    try:
        return symbol_store.get_domains()
    except Exception:
        raise HTTPException(status_code=500, detail="Could not retrieve domain list")
