"""
Naive vector-based retrieval using Qdrant.

Performs semantic search over document chunks using inLegalBERT embeddings.
"""

import logging
import time
from typing import List, Dict, Any, Optional

from .base import VectorRetriever, RetrievalResult

logger = logging.getLogger(__name__)


class QdrantVectorRetriever(VectorRetriever):
    """
    Vector retrieval using Qdrant collections.
    
    Retrieves document chunks based on semantic similarity to the query.
    Uses inLegalBERT embeddings (768-dimensional).
    """
    
    def __init__(self, collection_name: str = "legal_documents"):
        """
        Initialize Qdrant-based vector retriever.
        
        Args:
            collection_name: Name of Qdrant collection to search
        """
        self.collection_name = collection_name
        self._embedding_service = None
        self._qdrant_client = None
        self._init_clients()
    
    def _init_clients(self) -> None:
        """Initialize Qdrant client and embedding service."""
        try:
            from src.database.embeddings import InLegalBERTEmbeddingService
            from src.database.qdrant.client import get_qdrant_store
            
            self._embedding_service = InLegalBERTEmbeddingService()
            self._qdrant_client = get_qdrant_store()
        except Exception as e:
            logger.error(f"Failed to initialize Qdrant retriever: {e}")
            raise
    
    def get_embedding(self, text: str) -> List[float]:
        """Get inLegalBERT embedding for text."""
        if not self._embedding_service:
            raise RuntimeError("Embedding service not initialized")
        
        embeddings = self._embedding_service.embed_documents([text])
        return embeddings[0].tolist() if embeddings is not None else []
    
    def retrieve(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> RetrievalResult:
        """
        Retrieve document chunks similar to the query.
        
        Args:
            query: Query text
            top_k: Number of results to return
            filters: Optional metadata filters
            
        Returns:
            RetrievalResult with matched chunks
        """
        start_time = time.time()
        
        try:
            # Get query embedding
            query_embedding = self.get_embedding(query)
            
            if not query_embedding:
                logger.warning("Failed to generate query embedding")
                return RetrievalResult(
                    query=query,
                    results=[],
                    retrieval_type="naive",
                    total_results=0,
                    retrieval_time_ms=0
                )
            
            # Search Qdrant
            search_results = self._qdrant_client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                query_filter=filters,
                limit=top_k
            )
            
            # Format results
            results = []
            for result in search_results:
                results.append({
                    "id": result.id,
                    "score": result.score,
                    "text": result.payload.get("text", ""),
                    "metadata": {
                        k: v for k, v in result.payload.items()
                        if k != "text"
                    }
                })
            
            retrieval_time = (time.time() - start_time) * 1000
            
            return RetrievalResult(
                query=query,
                results=results,
                retrieval_type="naive",
                total_results=len(results),
                retrieval_time_ms=retrieval_time
            )
            
        except Exception as e:
            logger.error(f"Naive retrieval error: {e}", exc_info=True)
            raise
    
    def is_available(self) -> bool:
        """Check if Qdrant is available."""
        try:
            if not self._qdrant_client:
                return False
            # Try a simple health check
            collections = self._qdrant_client.get_collections()
            return True
        except Exception as e:
            logger.warning(f"Qdrant health check failed: {e}")
            return False
    
    def health_check(self) -> Dict[str, Any]:
        """Get health status of Qdrant."""
        try:
            collections = self._qdrant_client.get_collections()
            collection_names = [c.name for c in collections.collections]
            
            return {
                "status": "healthy",
                "backend": "qdrant",
                "collections": collection_names,
                "target_collection": self.collection_name,
                "collection_exists": self.collection_name in collection_names
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "backend": "qdrant",
                "error": str(e)
            }
