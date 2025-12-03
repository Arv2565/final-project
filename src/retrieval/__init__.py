"""
Query-time Retrieval Module.

Provides multiple retrieval strategies for the Legal AI Assistant:
- Naive: Vector-based semantic search over document chunks (Qdrant)
- Graph: Knowledge graph-based entity and relationship search (Neo4j)
- Hybrid: Combined vector and graph search with configurable weights

Usage:
    from src.retrieval import HybridRetrieval, get_retrieval_cache
    
    # Initialize hybrid retriever with weights
    retriever = HybridRetrieval(vector_weight=0.6, graph_weight=0.4)
    
    # Retrieve documents
    results = retriever.retrieve("contract breach damages", top_k=10)
    
    # Check health
    health = retriever.health_check()
"""

from .base import (
    Retriever,
    VectorRetriever,
    GraphRetriever,
    HybridRetriever,
    RetrievalResult,
)

from .naive import QdrantVectorRetriever
from .graph import Neo4jGraphRetriever
from .hybrid import HybridRetrieval

from .cache import (
    RetrievalCache,
    get_retrieval_cache,
    cache_retrieval_result,
    get_cached_result,
)

__all__ = [
    # Base classes
    "Retriever",
    "VectorRetriever",
    "GraphRetriever",
    "HybridRetriever",
    "RetrievalResult",
    
    # Implementations
    "QdrantVectorRetriever",
    "Neo4jGraphRetriever",
    "HybridRetrieval",
    
    # Caching
    "RetrievalCache",
    "get_retrieval_cache",
    "cache_retrieval_result",
    "get_cached_result",
]
