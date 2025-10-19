# app/routes.py

from typing import Annotated, List, Optional

import asyncio
import structlog
from fastapi import APIRouter, Body, HTTPException, Path, Query
from pydantic import BaseModel, Field

from app import symbol_store, symbol_sync
from app.inference import run_query
from app.logging_config import configure_logging
from app.symbol_store import Symbol


configure_logging()
log = structlog.get_logger(__name__)

router = APIRouter()


async def _fetch_external_domains(event_prefix: str) -> List[str]:
    """Load symbol domains from the managed store with consistent error handling."""

    try:
        domains = await asyncio.to_thread(symbol_sync.fetch_domains_from_external_store)
    except symbol_sync.ExternalSymbolStoreError as exc:
        log.error(f"{event_prefix}.external_error", error=str(exc))
        raise HTTPException(status_code=502, detail="Failed to retrieve domains") from exc
    except Exception as exc:  # pragma: no cover - defensive catch for unexpected issues
        log.error(f"{event_prefix}.error", error=str(exc))
        raise HTTPException(status_code=500, detail="Could not retrieve domain list") from exc

    log.info(f"{event_prefix}.completed", count=len(domains))
    return domains


class QueryRequest(BaseModel):
    query: str
    session_id: str


class SyncRequest(BaseModel):
    symbol_domain: Optional[str] = None
    symbol_tag: Optional[str] = None
    limit: int = Field(20, ge=1, le=20)


@router.post("/query")
async def query_inference(request: QueryRequest):
    log.info(
        "routes.query_inference",
        session_id=request.session_id,
        query_length=len(request.query),
    )
    result = run_query(request.query, request.session_id)
    log.info("routes.query_inference.completed", symbols=len(result.get("symbols_used", [])))
    return result


@router.get("/symbols")
async def get_symbols(
    symbol_domain: Optional[str] = Query(None),
    symbol_tag: Optional[str] = Query(None),
    start_index: Optional[int] = Query(0),
    limit: Optional[int] = Query(20, le=50),
):
    log.debug(
        "routes.get_symbols",
        domain=symbol_domain,
        tag=symbol_tag,
        start=start_index,
        limit=limit,
    )
    symbols = symbol_store.get_symbols(
        domain=symbol_domain, tag=symbol_tag, start=start_index, limit=limit
    )
    log.info("routes.get_symbols.completed", count=len(symbols))
    return symbols


@router.get("/symbol/{id}")
async def get_symbol_by_id(id: str = Path(..., description="Symbol ID")):
    log.debug("routes.get_symbol", symbol_id=id)
    symbol = symbol_store.get_symbol(id)
    if symbol is None:
        log.warning("routes.get_symbol.not_found", symbol_id=id)
        raise HTTPException(status_code=404, detail="Symbol not found")
    return symbol


@router.put("/inject/{symbol_id}")
async def put_symbol_by_id(
    symbol_id: str = Path(..., description="Symbol ID"),
    symbol: Symbol = Body(...),
):
    log.info("routes.put_symbol", symbol_id=symbol_id)
    status = symbol_store.put_symbol(symbol_id, symbol)
    return {"status": status}


@router.put("/inject/symbols")
async def bulk_put_symbols(symbols: Annotated[List[Symbol], Body(..., embed=True)]):
    log.info("routes.bulk_put_symbols", count=len(symbols))
    return {"status": symbol_store.put_symbols_bulk(symbols)}


@router.get("/domains")
async def list_domains():
    return await _fetch_external_domains("routes.list_domains")


@router.get("/sync/domains")
async def list_sync_domains():
    return await _fetch_external_domains("routes.sync_domains")


@router.post("/sync/symbols")
async def sync_symbols(request: SyncRequest):
    log.info(
        "routes.sync_symbols.begin",
        domain=request.symbol_domain,
        tag=request.symbol_tag,
        limit=request.limit,
    )

    try:
        result = await asyncio.to_thread(
            symbol_sync.sync_symbols_from_external_store,
            symbol_domain=request.symbol_domain,
            symbol_tag=request.symbol_tag,
            limit=request.limit,
        )
    except ValueError as exc:
        log.warning("routes.sync_symbols.invalid", error=str(exc))
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except symbol_sync.ExternalSymbolStoreError as exc:
        log.error("routes.sync_symbols.external_error", error=str(exc))
        raise HTTPException(
            status_code=502, detail="Failed to sync symbols from external store"
        ) from exc

    log.info(
        "routes.sync_symbols.completed",
        fetched=result.fetched,
        stored=result.stored,
        new=result.new,
        updated=result.updated,
        pages=result.pages,
    )
    return result.to_dict()
