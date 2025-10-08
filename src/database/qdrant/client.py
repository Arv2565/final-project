"""
Qdrant Client Module for Legal Document Ingestion Workflow.

This module implements Step 3 of the three-step process:
- Store embeddings with metadata in a Qdrant collection
- Manage collection creation and configuration
- Handle batch uploads and metadata indexing
- Provide production-ready error handling
"""

import uuid
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
import logging
import numpy as np

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import (
        VectorParams, Distance, CollectionStatus, PointStruct, 
        PayloadSchemaType, CreateFieldIndex, FieldCondition, 
        Filter, MatchValue, SearchRequest
    )
    from qdrant_client.http.exceptions import UnexpectedResponse
except ImportError:
    raise ImportError("qdrant-client is required. Install with: pip install qdrant-client")

from config.settings import get_settings
from processing.document_processor import DocumentChunk

logger = logging.getLogger(__name__)

class QdrantLegalDocumentStore:
    """
    Qdrant storage service for legal document embeddings.
    
    This service:
    - Manages Qdrant collections for legal documents
    - Stores embeddings with rich metadata
    - Provides indexing strategies for legal document fields
    - Handles batch operations for efficiency
    - Supports filtering and search operations
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.collection_name = self.settings.qdrant.collection_name
        self.client = self._create_client()
        self._ensure_collection_exists()
    
    def _create_client(self) -> QdrantClient:
        """Create and configure Qdrant client."""
        try:
            if self.settings.qdrant.api_key:
                client = QdrantClient(
                    host=self.settings.qdrant.host,
                    port=self.settings.qdrant.port,
                    api_key=self.settings.qdrant.api_key
                )
            else:
                client = QdrantClient(
                    host=self.settings.qdrant.host,
                    port=self.settings.qdrant.port
                )
            
            # Test connection
            collections = client.get_collections()
            logger.info(f"Connected to Qdrant at {self.settings.qdrant.host}:{self.settings.qdrant.port}")
            return client
            
        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {e}")
            raise ConnectionError(f"Cannot connect to Qdrant database: {e}")
    
    def _ensure_collection_exists(self):
        """Ensure the legal documents collection exists with proper configuration."""
        try:
            collections = self.client.get_collections()
            collection_names = [col.name for col in collections.collections]
            
            if self.collection_name not in collection_names:
                logger.info(f"Creating collection: {self.collection_name}")
                self._create_collection()
            else:
                logger.info(f"Collection '{self.collection_name}' already exists")
                self._verify_collection_config()
                
        except Exception as e:
            logger.error(f"Error checking collection existence: {e}")
            raise RuntimeError(f"Failed to ensure collection exists: {e}")
    
    def _create_collection(self):
        """Create the legal documents collection with proper configuration."""
        try:
            # Create collection with vector configuration
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.settings.qdrant.vector_size,
                    distance=Distance.COSINE if self.settings.qdrant.distance_metric == "cosine" else Distance.EUCLIDEAN
                )
            )
            
            # Create payload indexes for filtering
            self._create_payload_indexes()
            
            logger.info(f"Successfully created collection: {self.collection_name}")
            
        except Exception as e:
            logger.error(f"Failed to create collection: {e}")
            raise RuntimeError(f"Collection creation failed: {e}")
    
    def _create_payload_indexes(self):
        """Create indexes for legal document metadata fields."""
        indexed_fields = self.settings.get_indexed_fields()
        
        for field_name, should_index in indexed_fields.items():
            if should_index:
                try:
                    self.client.create_payload_index(
                        collection_name=self.collection_name,
                        field_name=field_name,
                        field_schema=PayloadSchemaType.KEYWORD
                    )
                    logger.info(f"Created index for field: {field_name}")
                except Exception as e:
                    logger.warning(f"Failed to create index for {field_name}: {e}")
    
    def _verify_collection_config(self):
        """Verify that existing collection has correct configuration."""
        try:
            collection_info = self.client.get_collection(self.collection_name)
            
            # Verify vector size
            vector_size = collection_info.config.params.vectors.size
            if vector_size != self.settings.qdrant.vector_size:
                logger.warning(f"Collection vector size ({vector_size}) doesn't match expected ({self.settings.qdrant.vector_size})")
            
            logger.info(f"Collection configuration verified")
            
        except Exception as e:
            logger.warning(f"Could not verify collection configuration: {e}")
    
    def store_document_chunks(self, chunk_embedding_pairs: List[tuple[DocumentChunk, np.ndarray]]) -> List[str]:
        """
        Store document chunks with their embeddings in Qdrant.
        
        Args:
            chunk_embedding_pairs: List of (chunk, embedding) tuples
            
        Returns:
            List of point IDs that were stored
        """
        if not chunk_embedding_pairs:
            logger.warning("No chunks provided for storage")
            return []
        
        points = []
        point_ids = []
        
        for chunk, embedding in chunk_embedding_pairs:
            # Generate unique point ID
            point_id = str(uuid.uuid4())
            point_ids.append(point_id)
            
            # Prepare payload (metadata)
            payload = self._prepare_payload(chunk)
            
            # Create point
            point = PointStruct(
                id=point_id,
                vector=embedding.tolist(),
                payload=payload
            )
            points.append(point)
        
        try:
            # Store points in batch
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            
            logger.info(f"Successfully stored {len(points)} document chunks in Qdrant")
            return point_ids
            
        except Exception as e:
            logger.error(f"Failed to store chunks in Qdrant: {e}")
            raise RuntimeError(f"Storage operation failed: {e}")
    
    def _prepare_payload(self, chunk: DocumentChunk) -> Dict[str, Any]:
        """
        Prepare payload (metadata) for a document chunk.
        
        Args:
            chunk: DocumentChunk to extract metadata from
            
        Returns:
            Dictionary containing the payload data
        """
        payload = chunk.metadata.copy()
        
        # Add chunk-specific metadata
        payload.update({
            "text": chunk.text,
            "chunk_id": chunk.chunk_id,
            "total_chunks": chunk.total_chunks,
            "source_file": chunk.source_file,
            "storage_timestamp": datetime.now().isoformat()
        })
        
        # Ensure all values are JSON serializable
        for key, value in payload.items():
            if value is None:
                payload[key] = ""
            elif not isinstance(value, (str, int, float, bool, list, dict)):
                payload[key] = str(value)
        
        return payload
    
    def search_similar_chunks(self, 
                            query_embedding: np.ndarray, 
                            limit: int = 10, 
                            score_threshold: float = 0.0,
                            filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Search for similar document chunks.
        
        Args:
            query_embedding: Query embedding vector
            limit: Maximum number of results to return
            score_threshold: Minimum similarity score threshold
            filters: Optional filters to apply (e.g., {"court": "Supreme Court"})
            
        Returns:
            List of search results with chunks and scores
        """
        try:
            # Prepare filter conditions
            filter_conditions = None
            if filters:
                filter_conditions = Filter(
                    must=[
                        FieldCondition(key=key, match=MatchValue(value=value))
                        for key, value in filters.items()
                    ]
                )
            
            # Perform search
            search_results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding.tolist(),
                query_filter=filter_conditions,
                limit=limit,
                score_threshold=score_threshold,
                with_payload=True,
                with_vectors=False
            )
            
            results = []
            for result in search_results:
                results.append({
                    "id": result.id,
                    "score": result.score,
                    "payload": result.payload,
                    "text": result.payload.get("text", ""),
                    "metadata": {k: v for k, v in result.payload.items() if k != "text"}
                })
            
            logger.info(f"Found {len(results)} similar chunks")
            return results
            
        except Exception as e:
            logger.error(f"Search operation failed: {e}")
            raise RuntimeError(f"Failed to search similar chunks: {e}")
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the collection."""
        try:
            collection_info = self.client.get_collection(self.collection_name)
            
            stats = {
                "collection_name": self.collection_name,
                "total_points": collection_info.points_count,
                "vector_size": collection_info.config.params.vectors.size,
                "distance_metric": collection_info.config.params.vectors.distance,
                "status": collection_info.status,
                "indexed_vectors": collection_info.indexed_vectors_count
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {"error": str(e)}
    
    def delete_points_by_filter(self, filters: Dict[str, Any]) -> bool:
        """
        Delete points matching the given filters.
        
        Args:
            filters: Filter conditions to match points for deletion
            
        Returns:
            True if deletion was successful
        """
        try:
            filter_conditions = Filter(
                must=[
                    FieldCondition(key=key, match=MatchValue(value=value))
                    for key, value in filters.items()
                ]
            )
            
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=filter_conditions
            )
            
            logger.info(f"Deleted points matching filters: {filters}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete points: {e}")
            return False
    
    def close(self):
        """Close the Qdrant client connection."""
        try:
            self.client.close()
            logger.info("Qdrant client connection closed")
        except Exception as e:
            logger.warning(f"Error closing Qdrant connection: {e}")

# Singleton instance for global use
_qdrant_store: Optional[QdrantLegalDocumentStore] = None

def get_qdrant_store() -> QdrantLegalDocumentStore:
    """Get the global Qdrant store instance."""
    global _qdrant_store
    if _qdrant_store is None:
        _qdrant_store = QdrantLegalDocumentStore()
    return _qdrant_store

def cleanup_qdrant_store():
    """Clean up the global Qdrant store."""
    global _qdrant_store
    if _qdrant_store:
        _qdrant_store.close()
        _qdrant_store = None