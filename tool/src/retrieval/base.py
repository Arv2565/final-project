"""
Abstract base classes for retrieval implementations.

Defines the interface for different retrieval strategies:
- Naive: Vector-based semantic search (Qdrant)
- Graph: Knowledge graph-based search (Neo4j)
- Hybrid: Combined vector and graph search
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class RetrievalResult:
    """Result of a retrieval query."""
    
    query: str
    results: List[Dict[str, Any]]
    retrieval_type: str  # 'naive', 'graph', 'hybrid'
    total_results: int
    retrieval_time_ms: float
    metadata: Dict[str, Any] = None


class Retriever(ABC):
    """Abstract base class for all retrieval implementations."""
    
    @abstractmethod
    def retrieve(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> RetrievalResult:
        """
        Retrieve documents/entities matching the query.
        
        Args:
            query: Query text
            top_k: Number of results to return
            filters: Optional filters to apply
            **kwargs: Implementation-specific arguments
            
        Returns:
            RetrievalResult containing matched items
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the retriever is properly configured and available."""
        pass
    
    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check of the retriever.
        
        Returns:
            Dictionary with health status and diagnostics
        """
        pass


class VectorRetriever(Retriever):
    """Base class for vector-based retrievers."""
    
    @abstractmethod
    def get_embedding(self, text: str) -> List[float]:
        """Get embedding for text."""
        pass


class GraphRetriever(Retriever):
    """Base class for graph-based retrievers."""
    
    @abstractmethod
    def expand_entity_neighbors(
        self,
        entity_id: str,
        hops: int = 1
    ) -> Dict[str, Any]:
        """Expand entity with its neighbors in the graph."""
        pass


class HybridRetriever(Retriever):
    """Base class for hybrid retrievers combining multiple strategies."""
    
    @abstractmethod
    def set_vector_weight(self, weight: float) -> None:
        """Set the weight for vector search in hybrid retrieval."""
        pass
    
    @abstractmethod
    def set_graph_weight(self, weight: float) -> None:
        """Set the weight for graph search in hybrid retrieval."""
        pass
