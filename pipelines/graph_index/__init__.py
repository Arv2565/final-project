"""
Graph Indexing Pipeline (GraphRAG).

Extracts entities and relationships from legal documents,
canonicalizes them, and indexes them into Neo4j.
"""

from .indexer import GraphRAGIndexer, Triple, TripleValidationResult
from .enrichment import normalize_name, canonicalize_entities_legal, enrich_relation
from .retrieval import GraphRetriever

__all__ = [
    "GraphRAGIndexer",
    "Triple",
    "TripleValidationResult",
    "normalize_name",
    "canonicalize_entities_legal",
    "enrich_relation",
    "GraphRetriever",
]
