"""Utilities for enforcing symbol validation invariants."""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from app.domain_types import Symbol


def _normalise_candidate(value: object) -> Iterable[str]:
    if isinstance(value, str):
        yield value
        return
    if isinstance(value, (list, tuple, set)):
        for item in value:
            if isinstance(item, str):
                yield item


def symbol_has_validated_trait(symbol: Mapping[str, Any] | Symbol | None) -> bool:
    """Return ``True`` when the payload marks the symbol as validated.

    The validation prompts instruct the model to persist only symbols that have
    been marked as ``"validated"``.  Symbols may communicate this either through
    an explicit ``status`` field or by including ``"validated"`` within a
    ``traits`` collection.  The helper understands both representations and is
    tolerant of additional fields.
    """

    if symbol is None:
        return False

    if isinstance(symbol, Symbol):
        payload: Mapping[str, Any] = symbol.model_dump()
    elif isinstance(symbol, Mapping):
        payload = symbol
    else:
        return False

    status = payload.get("status")
    if isinstance(status, str) and status.casefold() == "validated":
        return True

    traits = payload.get("traits")
    if traits is not None:
        for trait in _normalise_candidate(traits):
            if trait.casefold() == "validated":
                return True

    return False


__all__ = ["symbol_has_validated_trait"]

