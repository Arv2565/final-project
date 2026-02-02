"""
Hybrid retrieval combining vector and graph search.

Blends results from Qdrant (naive vector search) and Neo4j (graph search)
with configurable weights.
"""

import logging
import time
from typing import List, Dict, Any, Optional

from .base import HybridRetriever, RetrievalResult
from .naive import QdrantVectorRetriever
from .graph import Neo4jGraphRetriever

logger = logging.getLogger(__name__)


class HybridRetrieval(HybridRetriever):
    """
    Hybrid retrieval combining vector and graph search.
    
    - Vector search: Fast semantic matching over document chunks
    - Graph search: Structured entity and relationship retrieval
    - Combined: Blended results with configurable weights
    """
    
    def __init__(
        self,
        vector_weight: float = 0.5,
        graph_weight: float = 0.5,
        collection_name: str = "legal_documents",
        vector_index: str = "entity_embedding_index"
    ):
        """
        Initialize hybrid retriever.
        
        Args:
            vector_weight: Weight for vector search results (0-1)
            graph_weight: Weight for graph search results (0-1)
            collection_name: Qdrant collection name
            vector_index: Neo4j vector index name
        """
        self.vector_weight = vector_weight
        self.graph_weight = graph_weight
        
        self._vector_retriever = QdrantVectorRetriever(collection_name)
        self._graph_retriever = Neo4jGraphRetriever(vector_index)
    
    def set_vector_weight(self, weight: float) -> None:
        """Set the weight for vector search in hybrid retrieval."""
        if not 0 <= weight <= 1:
            raise ValueError("Weight must be between 0 and 1")
        self.vector_weight = weight
        self.graph_weight = 1 - weight
    
    def set_graph_weight(self, weight: float) -> None:
        """Set the weight for graph search in hybrid retrieval."""
        if not 0 <= weight <= 1:
            raise ValueError("Weight must be between 0 and 1")
        self.graph_weight = weight
        self.vector_weight = 1 - weight
    
    def retrieve(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> RetrievalResult:
        """
        Retrieve documents using combined vector and graph search.
        
        Args:
            query: Query text
            top_k: Number of results to return
            filters: Optional filters for vector search
            
        Returns:
            RetrievalResult with blended results
        """
        start_time = time.time()
        all_results = []
        metadata = {
            "vector_weight": self.vector_weight,
            "graph_weight": self.graph_weight,
            "subquery_timing": {}
        }
        
        try:
            # Run vector retrieval
            if self.vector_weight > 0:
                try:
                    vector_start = time.time()
                    vector_results = self._vector_retriever.retrieve(
                        query=query,
                        top_k=top_k,
                        filters=filters
                    )
                    metadata["subquery_timing"]["vector_ms"] = (
                        time.time() - vector_start
                    ) * 1000
                    
                    # Weight vector results
                    for result in vector_results.results:
                        result["weighted_score"] = (
                            result.get("score", 0) * self.vector_weight
                        )
                        result["source"] = "vector"
                    all_results.extend(vector_results.results)
                except Exception as e:
                    logger.error(f"Vector retrieval failed: {e}")
                    metadata["vector_error"] = str(e)
            
            # Run graph retrieval
            if self.graph_weight > 0:
                try:
                    graph_start = time.time()
                    graph_results = self._graph_retriever.retrieve(
                        query=query,
                        top_k=top_k
                    )
                    metadata["subquery_timing"]["graph_ms"] = (
                        time.time() - graph_start
                    ) * 1000
                    
                    # Weight graph results
                    for i, result in enumerate(graph_results.results):
                        # Use inverse rank as score for graph results
                        rank_score = 1.0 / (i + 1)
                        result["weighted_score"] = rank_score * self.graph_weight
                        result["source"] = "graph"
                    all_results.extend(graph_results.results)
                except Exception as e:
                    logger.error(f"Graph retrieval failed: {e}")
                    metadata["graph_error"] = str(e)
            
            # Sort by weighted score and deduplicate
            all_results.sort(
                key=lambda x: x.get("weighted_score", 0),
                reverse=True
            )
            
            # Limit to top_k
            final_results = all_results[:top_k]
            
            retrieval_time = (time.time() - start_time) * 1000
            
            return RetrievalResult(
                query=query,
                results=final_results,
                retrieval_type="hybrid",
                total_results=len(final_results),
                retrieval_time_ms=retrieval_time,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Hybrid retrieval error: {e}", exc_info=True)
            raise
    
    def is_available(self) -> bool:
        """Check if both retrieval backends are available."""
        vector_ok = self._vector_retriever.is_available()
        graph_ok = self._graph_retriever.is_available()
        
        # Both must be available for hybrid retrieval
        return vector_ok and graph_ok
    
    def health_check(self) -> Dict[str, Any]:
        """Get health status of both retrieval backends."""
        return {
            "status": "healthy" if self.is_available() else "unhealthy",
            "type": "hybrid",
            "vector": self._vector_retriever.health_check(),
            "graph": self._graph_retriever.health_check(),
            "weights": {
                "vector": self.vector_weight,
                "graph": self.graph_weight
            }
        }
