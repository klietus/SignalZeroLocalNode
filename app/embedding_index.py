"""Symbol embedding index utilities with optional lightweight backend."""
from __future__ import annotations

import math
import os
import random
from typing import Dict, Iterable, List, Sequence, Tuple

import structlog

try:  # pragma: no cover - exercised implicitly when deps available
    import faiss  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    faiss = None  # type: ignore

try:  # pragma: no cover - exercised implicitly when deps available
    import numpy as np  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    np = None  # type: ignore

try:  # pragma: no cover - exercised implicitly when deps available
    from sentence_transformers import SentenceTransformer  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    SentenceTransformer = None  # type: ignore

from app.logging_config import configure_logging
from app.types import Symbol


configure_logging()
log = structlog.get_logger(__name__)


class _SimpleEncoder:
    """Deterministic text encoder used when sentence-transformers is unavailable."""

    def __init__(self, dimension: int):
        self.dimension = dimension

    def encode(self, text: str) -> List[float]:
        rng = random.Random()
        rng.seed(text)
        vector = [rng.random() for _ in range(self.dimension)]
        log.debug("embedding_index.simple_encoder", dimension=self.dimension)
        return vector


class _InMemoryIndex:
    """Lightweight in-memory index used as a fallback when FAISS is unavailable."""

    def __init__(self, dimension: int):
        self.dimension = dimension
        self.reset()

    def reset(self) -> None:
        self._vectors: List[List[float]] = []
        log.debug("embedding_index.reset")

    def add(self, vectors: Sequence[Sequence[float]]) -> None:
        added = 0
        for vector in vectors:
            self._vectors.append([float(v) for v in vector])
            added += 1
        log.debug("embedding_index.added_vectors", count=added)

    def search(
        self, query_vectors: Sequence[Sequence[float]], k: int
    ) -> Tuple[List[List[float]], List[List[int]]]:
        if not query_vectors:
            return [[float("inf") for _ in range(k)]], [[-1 for _ in range(k)]]

        query = list(query_vectors[0])
        distances: List[Tuple[float, int]] = []

        for idx, vector in enumerate(self._vectors):
            if not vector:
                continue
            # Euclidean distance
            dist = math.sqrt(
                sum((float(a) - float(b)) ** 2 for a, b in zip(query, vector))
            )
            distances.append((dist, idx))

        distances.sort(key=lambda item: item[0])
        top = distances[:k]

        dists = [dist for dist, _ in top]
        indices = [idx for _, idx in top]

        while len(dists) < k:
            dists.append(float("inf"))
            indices.append(-1)

        log.debug("embedding_index.search_results", count=len(distances))
        return [dists], [indices]

    @property
    def is_trained(self) -> bool:
        return bool(self._vectors)

    @property
    def ntotal(self) -> int:
        return len(self._vectors)


_BACKEND = os.getenv("EMBEDDING_INDEX_BACKEND", "auto").lower()
_HAS_FAISS_STACK = (
    faiss is not None
    and np is not None
    and SentenceTransformer is not None
)

_USE_FAISS = (_BACKEND == "faiss" and _HAS_FAISS_STACK) or (
    _BACKEND == "auto" and _HAS_FAISS_STACK
)

if _BACKEND == "faiss" and not _HAS_FAISS_STACK:
    # Explicit faiss backend requested but dependencies missing; fall back gracefully.
    log.warning("embedding_index.faiss_unavailable", backend=_BACKEND)
    _USE_FAISS = False

_DIMENSION = 384 if _USE_FAISS else 32


def _create_encoder():
    if _USE_FAISS and SentenceTransformer is not None:
        log.info("embedding_index.encoder_initialised", backend="sentence_transformers")
        return SentenceTransformer("all-MiniLM-L6-v2")
    log.info("embedding_index.encoder_initialised", backend="simple")
    return _SimpleEncoder(_DIMENSION)


def _create_index():
    if _USE_FAISS and faiss is not None:
        log.info("embedding_index.backend", implementation="faiss", dimension=_DIMENSION)
        return faiss.IndexFlatL2(_DIMENSION)
    log.info("embedding_index.backend", implementation="in_memory", dimension=_DIMENSION)
    return _InMemoryIndex(_DIMENSION)


model = _create_encoder()
index = _create_index()
symbol_index_map: Dict[str, int] = {}
index_data: List[Iterable[float]] = []


def _encode_for_storage(text: str):
    vector = model.encode(text)
    if _USE_FAISS:
        assert np is not None  # for type checkers
        if not isinstance(vector, np.ndarray):
            vector = np.asarray(vector, dtype="float32")
        return vector.astype("float32")
    return [float(v) for v in vector]


def _refresh_index() -> None:
    index.reset()
    if not index_data:
        log.info("embedding_index.refresh_skipped")
        return
    if _USE_FAISS:
        assert np is not None
        stacked = np.stack(list(index_data)).astype("float32")
        index.add(stacked)
    else:
        index.add(index_data)  # type: ignore[arg-type]
    log.info("embedding_index.refreshed", entries=len(index_data))


def build_index() -> None:
    """Build the embedding index from persisted symbols."""

    global symbol_index_map, index_data
    from app.symbol_store import get_symbols

    symbols = get_symbols(domain=None, tag=None, start=0, limit=10000)

    symbol_index_map = {}
    index_data = []

    for symbol in symbols:
        if not getattr(symbol, "macro", None):
            log.debug("embedding_index.symbol_skipped", symbol_id=symbol.id)
            continue
        vector = _encode_for_storage(symbol.macro)
        symbol_index_map[symbol.id] = len(index_data)
        index_data.append(vector)

    _refresh_index()
    log.info("embedding_index.built", count=len(index_data))


def add_symbol(symbol: Symbol) -> None:
    """Add or update a single symbol in the embedding index."""

    if not getattr(symbol, "macro", None):
        log.debug("embedding_index.add_skipped", symbol_id=getattr(symbol, "id", None))
        return

    vector = _encode_for_storage(symbol.macro)
    sid = symbol.id

    if sid in symbol_index_map:
        position = symbol_index_map[sid]
        index_data[position] = vector
        log.debug("embedding_index.updated_symbol", symbol_id=sid)
    else:
        symbol_index_map[sid] = len(index_data)
        index_data.append(vector)
        log.debug("embedding_index.added_symbol", symbol_id=sid)

    _refresh_index()


def search(query: str, k: int = 5) -> List[Tuple[str, float]]:
    """Search for the most relevant symbols given a text query."""

    if not getattr(index, "is_trained", False) or getattr(index, "ntotal", 0) == 0:
        log.debug("embedding_index.rebuild_required")
        build_index()

    query_vector = _encode_for_storage(query)

    if _USE_FAISS:
        assert np is not None
        matrix = query_vector.reshape(1, -1)  # type: ignore[union-attr]
    else:
        matrix = [query_vector]

    distances, indices = index.search(matrix, k)

    reverse_map = {v: k for k, v in symbol_index_map.items()}
    results: List[Tuple[str, float]] = []

    for idx, dist in zip(indices[0], distances[0]):
        sid = reverse_map.get(idx)
        if sid is not None:
            results.append((sid, float(dist)))

    log.info("embedding_index.search_completed", query_length=len(query), results=len(results))
    return results
