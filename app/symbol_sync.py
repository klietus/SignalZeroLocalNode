"""Utilities for synchronizing symbols from the external SignalZero store."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import List, Optional

import httpx
import structlog
from pydantic import ValidationError

from app.config import get_settings
from app.domain_types import Symbol
from app.logging_config import configure_logging
from app import symbol_store

configure_logging()
log = structlog.get_logger(__name__)


class ExternalSymbolStoreError(RuntimeError):
    """Raised when communication with the external store fails."""


@dataclass
class SyncResult:
    """Summary of a synchronization run."""

    fetched: int = 0
    stored: int = 0
    new: int = 0
    updated: int = 0
    pages: int = 0

    def to_dict(self) -> dict:
        """Return the synchronization summary as a JSON-serialisable dictionary."""

        return asdict(self)


class ExternalSymbolStoreClient:
    """HTTP client for interacting with the managed SignalZero symbol store."""

    def __init__(
        self,
        base_url: str,
        *,
        timeout: float = 10.0,
        client: Optional[httpx.Client] = None,
        **client_kwargs,
    ) -> None:
        if client is not None and client_kwargs:
            raise ValueError("Client kwargs are not supported when an httpx.Client is provided")

        if client is None:
            self._client = httpx.Client(
                base_url=base_url,
                timeout=timeout,
                **client_kwargs,
            )
            self._owns_client = True
        else:
            self._client = client
            self._owns_client = False

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> "ExternalSymbolStoreClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def query_symbols(
        self,
        *,
        symbol_domain: Optional[str] = None,
        symbol_tag: Optional[str] = None,
        last_symbol_id: Optional[str] = None,
        limit: int = 20,
    ) -> List[Symbol]:
        params = {"limit": min(limit, 20)}
        if symbol_domain:
            params["symbol_domain"] = symbol_domain
        if symbol_tag:
            params["symbol_tag"] = symbol_tag
        if last_symbol_id:
            params["last_symbol_id"] = last_symbol_id

        log.debug("symbol_sync.query_symbols", params=params)
        try:
            response = self._client.get("/symbol", params=params)
            response.raise_for_status()
        except httpx.HTTPError as exc:  # pragma: no cover - http errors are unlikely in tests
            raise ExternalSymbolStoreError(str(exc)) from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise ExternalSymbolStoreError("Invalid JSON response from external store") from exc

        if not isinstance(payload, list):
            raise ExternalSymbolStoreError("Unexpected response format from external store")

        symbols: List[Symbol] = []
        for item in payload:
            try:
                symbols.append(Symbol.model_validate(item))
            except ValidationError as exc:
                log.warning(
                    "symbol_sync.symbol_validation_failed",
                    error=str(exc),
                    payload=item,
                )
        log.debug(
            "symbol_sync.query_symbols.completed",
            requested=limit,
            returned=len(symbols),
            params=params,
        )
        return symbols

    def list_domains(self) -> List[str]:
        """Return all symbol domains provided by the managed store."""

        log.debug("symbol_sync.list_domains.begin")
        try:
            response = self._client.get("/domains")
            response.raise_for_status()
        except httpx.HTTPError as exc:  # pragma: no cover - network failures are rare in tests
            raise ExternalSymbolStoreError(str(exc)) from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise ExternalSymbolStoreError("Invalid JSON response from external store") from exc

        if not isinstance(payload, list) or any(not isinstance(item, str) for item in payload):
            raise ExternalSymbolStoreError("Unexpected response format from external store")

        log.debug("symbol_sync.list_domains.completed", count=len(payload))
        return payload

def sync_symbols_from_external_store(
    *,
    symbol_domain: Optional[str] = None,
    symbol_tag: Optional[str] = None,
    limit: int = 20,
    client: Optional[ExternalSymbolStoreClient] = None,
) -> SyncResult:
    """Synchronise symbols from the managed store into the local Redis cache."""

    if limit <= 0:
        raise ValueError("limit must be greater than zero")

    limit = min(limit, 20)

    settings = get_settings()
    owns_client = False
    if client is None:
        client = ExternalSymbolStoreClient(
            settings.symbol_store_base_url, timeout=settings.symbol_store_timeout
        )
        owns_client = True

    result = SyncResult()
    last_symbol_id: Optional[str] = None

    try:
        while True:
            batch = client.query_symbols(
                symbol_domain=symbol_domain,
                symbol_tag=symbol_tag,
                last_symbol_id=last_symbol_id,
                limit=limit,
            )
            if not batch:
                break

            result.pages += 1
            result.fetched += len(batch)

            ids = [symbol.id for symbol in batch]
            existing_symbols = symbol_store.get_symbols_by_ids(ids)
            existing_ids = {symbol.id for symbol in existing_symbols}

            new_count = sum(1 for symbol_id in ids if symbol_id not in existing_ids)
            result.new += new_count
            result.updated += len(ids) - new_count

            symbol_store.put_symbols_bulk(batch)
            result.stored += len(batch)

            last_symbol_id = batch[-1].id
            if len(batch) < limit:
                break
    finally:
        if owns_client:
            client.close()

    log.info(
        "symbol_sync.sync_completed",
        fetched=result.fetched,
        stored=result.stored,
        new=result.new,
        updated=result.updated,
        pages=result.pages,
        domain=symbol_domain,
        tag=symbol_tag,
    )

    return result


def fetch_domains_from_external_store(
    *, client: Optional[ExternalSymbolStoreClient] = None
) -> List[str]:
    """Retrieve symbol domains directly from the managed store."""

    settings = get_settings()
    owns_client = False
    if client is None:
        client = ExternalSymbolStoreClient(
            settings.symbol_store_base_url, timeout=settings.symbol_store_timeout
        )
        owns_client = True

    try:
        domains = client.list_domains()
    finally:
        if owns_client:
            client.close()

    log.info("symbol_sync.fetch_domains.completed", count=len(domains))
    return domains
