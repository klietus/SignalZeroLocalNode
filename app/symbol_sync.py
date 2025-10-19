"""Utilities for synchronizing symbols from the external SignalZero store."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import List, Optional, Tuple
from urllib.parse import parse_qs, urlparse

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


@dataclass
class QueryPage:
    """Container for a single page returned from the external store."""

    symbols: List[Symbol]
    next_cursor: Optional[str]


def _decode_cursor(cursor: Optional[str]) -> Tuple[Optional[str], Optional[int]]:
    """Normalise cursor strings into explicit pagination inputs.

    The external store may return the cursor as a bare symbol ID, a query-string fragment,
    or a fully-qualified URL. This helper extracts the ``last_symbol_id`` (or other cursor
    identifiers) alongside an optional ``limit`` override so follow-up requests match the
    provided pagination contract.
    """

    if cursor is None:
        return None, None

    value = cursor.strip()
    if not value:
        return None, None

    query_string = ""

    if value.startswith(("http://", "https://")):
        parsed = urlparse(value)
        query_string = parsed.query
    elif "?" in value:
        query_string = value.split("?", 1)[1]
    elif "=" in value:
        query_string = value
    else:
        return value, None

    if not query_string:
        return None, None

    params = parse_qs(query_string, keep_blank_values=False)

    cursor_keys = ("last_symbol_id", "lastSymbolId", "cursor", "next")
    last_symbol_id = None
    for key in cursor_keys:
        values = params.get(key)
        if values:
            last_symbol_id = values[0].strip() or None
            if last_symbol_id:
                break

    limit_values = params.get("limit")
    limit_override: Optional[int] = None
    if limit_values:
        try:
            limit_override = int(limit_values[0])
        except (TypeError, ValueError):
            limit_override = None

    return last_symbol_id, limit_override


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
    ) -> QueryPage:
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
        except httpx.HTTPStatusError as exc:  # pragma: no cover - network errors are unlikely in tests
            detail = exc.response.text if exc.response is not None else ""
            message = detail or str(exc)
            if exc.response is not None and exc.response.status_code == 400:
                raise ValueError(
                    f"External store rejected the request: {message.strip() or '400 Bad Request'}"
                ) from exc
            raise ExternalSymbolStoreError(message) from exc
        except httpx.HTTPError as exc:  # pragma: no cover - other http errors are unlikely in tests
            raise ExternalSymbolStoreError(str(exc)) from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise ExternalSymbolStoreError("Invalid JSON response from external store") from exc

        items: List[dict]
        next_cursor: Optional[str] = None

        if isinstance(payload, list):
            items = payload
        elif isinstance(payload, dict):
            data_candidates: Tuple[Optional[List[dict]], ...] = (
                payload.get("symbols"),
                payload.get("items"),
                payload.get("data"),
            )
            items = next((candidate for candidate in data_candidates if isinstance(candidate, list)), None)
            if items is None:
                raise ExternalSymbolStoreError("Unexpected response format from external store")
            next_cursor_value = payload.get("last_symbol_id") or payload.get("next")
            if isinstance(next_cursor_value, str) and next_cursor_value.strip():
                next_cursor = next_cursor_value.strip()
        else:
            raise ExternalSymbolStoreError("Unexpected response format from external store")

        symbols: List[Symbol] = []
        for item in items:
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
        return QueryPage(symbols=symbols, next_cursor=next_cursor)

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

    current_limit = limit

    try:
        while True:
            page = client.query_symbols(
                symbol_domain=symbol_domain,
                symbol_tag=symbol_tag,
                last_symbol_id=last_symbol_id,
                limit=current_limit,
            )
            batch = page.symbols

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

            next_cursor_value, next_limit_override = _decode_cursor(page.next_cursor)

            if next_limit_override is not None:
                current_limit = max(1, min(next_limit_override, 20))

            if next_cursor_value:
                last_symbol_id = next_cursor_value
            elif page.next_cursor:
                last_symbol_id = page.next_cursor
            else:
                last_symbol_id = batch[-1].id

            if len(batch) < current_limit and not page.next_cursor:
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
