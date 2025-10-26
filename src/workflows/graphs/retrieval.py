"""Combined graph + vector retrieval helpers.

Provides a simple retrieval flow that: 1) computes an embedding for the query,
2) fetches candidate entities with embeddings from Neo4j, 3) computes cosine
similarity in Python and returns top-k seed entities, and 4) optionally expands
using graph traversal.

This implementation is intentionally conservative: it fetches embeddings into
Python and ranks there to avoid relying on Neo4j vector features that may not
be available in every deployment.
"""
from __future__ import annotations

import logging
from typing import List, Tuple, Dict, Any
import numpy as np

from database.neo4j.client import neo4j_session
from database.embeddings import get_embedding_service

logger = logging.getLogger(__name__)


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    if a is None or b is None:
        return -1.0
    a = np.asarray(a)
    b = np.asarray(b)
    if a.size == 0 or b.size == 0:
        return -1.0
    denom = (np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0:
        return -1.0
    return float(np.dot(a, b) / denom)


def vector_nearest_entities(query: str, top_k: int = 10) -> List[Tuple[str, float, Dict[str, Any]]]:
    """Return top_k entity names with a similarity score and node metadata.

    Strategy:
    - Use project's embedding service to get a query vector
    - Pull back nodes from Neo4j that have embeddings and compute cosine in Python
    - Return top_k
    """
    emb_service = get_embedding_service()
    q_vec = emb_service.embed_single_text(query)
    candidates = []
    with neo4j_session() as session:
        # retrieve entities with non-null embedding
        res = session.run("MATCH (e:Entity) WHERE e.embedding IS NOT NULL RETURN e.name as name, e.embedding as embedding, e {.*} as meta LIMIT 10000")
        for rec in res:
            name = rec.get("name")
            vec = rec.get("embedding")
            meta = rec.get("meta") or {}
            candidates.append((name, vec, meta))

    scored = []
    for name, vec, meta in candidates:
        try:
            score = _cosine(np.array(q_vec), np.array(vec))
        except Exception:
            score = -1.0
        scored.append((name, score, meta))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_k]


def expand_graph_seeds(seeds: List[str], hops: int = 1, limit_per_seed: int = 10) -> Dict[str, List[Dict[str, Any]]]:
    """Expand seeds by traversing RELATION edges up to `hops` and return connected nodes.

    Returns mapping seed -> list of neighbor node dicts: {name, relation, meta}
    """
    out = {}
    with neo4j_session() as session:
        for s in seeds:
            q = (
                "MATCH (a:Entity {name:$name})- [r:RELATION] -> (b:Entity) "
                "RETURN b.name as name, r.type as relation, r.source as source LIMIT $limit"
            )
            res = session.run(q, name=s, limit=limit_per_seed)
            neighbors = []
            for rec in res:
                neighbors.append({"name": rec.get("name"), "relation": rec.get("relation"), "source": rec.get("source")})
            out[s] = neighbors
    return out
