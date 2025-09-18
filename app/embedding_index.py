import faiss
import numpy as np
from typing import List, Tuple
from sentence_transformers import SentenceTransformer
from app.types import Symbol

model = SentenceTransformer("all-MiniLM-L6-v2")
dimension = 384
index = faiss.IndexFlatL2(dimension)
symbol_index_map: dict[str, int] = {}
index_data: List[np.ndarray] = []

def build_index():
    global index, symbol_index_map, index_data
    from app.symbol_store import get_symbols
    symbols = get_symbols(domain=None, tag=None, start=0, limit=10000)
    symbol_index_map.clear()
    index_data.clear()

    embeddings = []
    for idx, s in enumerate(symbols):
        if s.macro:
            emb = model.encode(s.macro).astype("float32")
            embeddings.append(emb)
            symbol_index_map[s.id] = idx
            index_data.append(emb)

    if embeddings:
        index.reset()
        index.add(np.array(embeddings).astype("float32"))

def add_symbol(symbol: Symbol):
    global index_data, symbol_index_map

    if not symbol.macro:
        return

    emb = model.encode(symbol.macro).astype("float32")
    sid = symbol.id

    if sid in symbol_index_map:
        # Overwrite old vector
        pos = symbol_index_map[sid]
        index_data[pos] = emb
    else:
        # New symbol
        symbol_index_map[sid] = len(index_data)
        index_data.append(emb)

    # Rebuild index
    vectors = np.array(index_data).astype("float32")
    index.reset()
    index.add(vectors)

def search(query: str, k: int = 5) -> List[Tuple[str, float]]:
    if not index.is_trained or index.ntotal == 0:
        build_index()

    query_emb = model.encode(query).astype("float32").reshape(1, -1)
    distances, indices = index.search(query_emb, k)

    # Invert the index map
    reverse_map = {v: k for k, v in symbol_index_map.items()}

    results = []
    for idx, dist in zip(indices[0], distances[0]):
        sid = reverse_map.get(idx)
        if sid:
            results.append((sid, float(dist)))

    return results

