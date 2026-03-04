"""
Qdrant Case Collection Setup for Case Retrieval Module.

This module manages the dedicated Qdrant collection for legal cases (`legal_cases`),
separate from the generic legal documents collection (`legal_documents`).

Handles:
- Collection creation with case-specific configuration
- Semantic-aware chunking (issue, ratio, statute, holding)
- Metadata indexing for case-specific fields
- Case document storage and retrieval
"""

import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import (
        VectorParams, Distance, PointStruct, PayloadSchemaType, 
        CreateFieldIndex, FieldCondition, Filter, MatchValue
    )
except ImportError:
    raise ImportError("qdrant-client is required. Install with: pip install qdrant-client")

from src.config import get_settings

logger = logging.getLogger(__name__)


class CaseVector:
    """Represents a single case chunk with metadata for Qdrant storage."""
    
    def __init__(
        self,
        case_id: str,
        chunk_id: int,
        total_chunks: int,
        chunk_text: str,
        embedding: List[float],
        content_type: str,  # issue, ratio, statute, holding
        metadata: Dict[str, Any]
    ):
        self.point_id = str(uuid.uuid4())
        self.case_id = case_id
        self.chunk_id = chunk_id
        self.total_chunks = total_chunks
        self.chunk_text = chunk_text
        self.embedding = embedding
        self.content_type = content_type
        self.metadata = metadata
        self.created_at = datetime.utcnow().isoformat()
    
    def to_point_struct(self) -> PointStruct:
        """Convert to Qdrant PointStruct for storage."""
        payload = {
            "case_id": self.case_id,
            "chunk_id": self.chunk_id,
            "total_chunks": self.total_chunks,
            "chunk_text": self.chunk_text,
            "content_type": self.content_type,
            "created_at": self.created_at,
            **self.metadata
        }
        
        return PointStruct(
            id=int(self.point_id.replace("-", "")[:16]),  # Convert UUID to numeric ID
            vector=self.embedding,
            payload=payload
        )


class QdrantCaseCollectionManager:
    """
    Manages the Qdrant collection for legal cases.
    
    Creates and maintains the `legal_cases` collection with:
    - Semantic-aware chunking strategy
    - Rich metadata indexing for case filtering
    - Court hierarchy filtering capabilities
    - Case-specific search operations
    """
    
    COLLECTION_NAME = "legal_cases"
    
    def __init__(self):
        """Initialize case collection manager."""
        self.settings = get_settings()
        self.client = self._create_client()
        self._ensure_collection_exists()
    
    def _create_client(self) -> QdrantClient:
        """Create Qdrant client connection."""
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
            client.get_collections()
            logger.info(f"Connected to Qdrant for case collection at {self.settings.qdrant.host}:{self.settings.qdrant.port}")
            return client
            
        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {e}")
            raise ConnectionError(f"Cannot connect to Qdrant: {e}")
    
    def _ensure_collection_exists(self):
        """Ensure the legal_cases collection exists with proper configuration."""
        try:
            collections = self.client.get_collections()
            collection_names = [col.name for col in collections.collections]
            
            if self.COLLECTION_NAME not in collection_names:
                logger.info(f"Creating collection: {self.COLLECTION_NAME}")
                self._create_collection()
            else:
                logger.info(f"Collection '{self.COLLECTION_NAME}' already exists")
                self._verify_collection_config()
                
        except Exception as e:
            logger.error(f"Error checking collection existence: {e}")
            raise RuntimeError(f"Failed to ensure collection exists: {e}")
    
    def _create_collection(self):
        """Create the legal_cases collection with semantic chunking support."""
        try:
            self.client.create_collection(
                collection_name=self.COLLECTION_NAME,
                vectors_config=VectorParams(
                    size=self.settings.qdrant.vector_size,  # 768 for inLegalBERT
                    distance=Distance.COSINE
                )
            )
            
            logger.info(f"Created collection: {self.COLLECTION_NAME}")
            
            # Create metadata indexes for case-specific filtering
            self._create_case_indexes()
            
        except Exception as e:
            logger.error(f"Failed to create collection: {e}")
            raise RuntimeError(f"Collection creation failed: {e}")
    
    def _create_case_indexes(self):
        """Create indexes for case-specific metadata fields."""
        # Define fields to index
        indexed_fields = {
            # Case identification
            "case_id": PayloadSchemaType.KEYWORD,
            "citation": PayloadSchemaType.KEYWORD,
            
            # Court information
            "court": PayloadSchemaType.KEYWORD,
            "court_level": PayloadSchemaType.INTEGER,  # 1=Supreme, 2=High, 3=Lower
            
            # Case metadata
            "date": PayloadSchemaType.KEYWORD,  # ISO format for range queries
            "year": PayloadSchemaType.INTEGER,
            "case_type": PayloadSchemaType.KEYWORD,  # Criminal, Civil, Constitutional, etc.
            
            # Content classification
            "content_type": PayloadSchemaType.KEYWORD,  # issue, ratio, statute, holding
            "legal_domain": PayloadSchemaType.KEYWORD,
            
            # Legal content tags
            "legal_concepts": PayloadSchemaType.KEYWORD,  # Stored as array of strings
            "statutes_mentioned": PayloadSchemaType.KEYWORD,
            "key_offences": PayloadSchemaType.KEYWORD,
            
            # Outcome information
            "decision": PayloadSchemaType.KEYWORD,
            "relief_type": PayloadSchemaType.KEYWORD,
            "reversal_indicators": PayloadSchemaType.KEYWORD,
            
            # Parties
            "parties_appellant": PayloadSchemaType.KEYWORD,
            "parties_respondent": PayloadSchemaType.KEYWORD,
            
            # Chunk organization
            "chunk_id": PayloadSchemaType.INTEGER,
            "total_chunks": PayloadSchemaType.INTEGER,
        }
        
        for field_name, schema_type in indexed_fields.items():
            try:
                self.client.create_payload_index(
                    collection_name=self.COLLECTION_NAME,
                    field_name=field_name,
                    field_schema=schema_type
                )
                logger.debug(f"Created index for field: {field_name}")
            except Exception as e:
                # Index might already exist, which is fine
                if "already exists" not in str(e).lower():
                    logger.warning(f"Failed to create index for {field_name}: {e}")
    
    def _verify_collection_config(self):
        """Verify existing collection configuration."""
        try:
            collection_info = self.client.get_collection(self.COLLECTION_NAME)
            vector_size = collection_info.config.params.vectors.size
            
            if vector_size != self.settings.qdrant.vector_size:
                logger.warning(
                    f"Collection vector size ({vector_size}) doesn't match "
                    f"expected ({self.settings.qdrant.vector_size})"
                )
            
            logger.info(f"Case collection verified: {collection_info.points_count} points")
            
        except Exception as e:
            logger.warning(f"Could not verify collection configuration: {e}")
    
    def store_case_chunks(self, case_vectors: List[CaseVector]) -> int:
        """
        Store case chunks (with embeddings) in Qdrant collection.
        
        Args:
            case_vectors: List of CaseVector objects to store
        
        Returns:
            Number of vectors successfully stored
        
        Raises:
            RuntimeError: If storage fails
        """
        if not case_vectors:
            logger.warning("No case vectors to store")
            return 0
        
        try:
            points = [vector.to_point_struct() for vector in case_vectors]
            
            self.client.upsert(
                collection_name=self.COLLECTION_NAME,
                points=points
            )
            
            logger.info(f"Successfully stored {len(case_vectors)} case chunks in Qdrant")
            return len(case_vectors)
            
        except Exception as e:
            logger.error(f"Failed to store case chunks: {e}")
            raise RuntimeError(f"Case chunk storage failed: {e}")
    
    def search_cases(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        score_threshold: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Search case collection using vector similarity.
        
        Args:
            query_embedding: Query vector (768-dim)
            top_k: Number of results to return
            filters: Qdrant filters for metadata filtering
            score_threshold: Minimum similarity score
        
        Returns:
            List of matching cases with metadata and scores
        """
        try:
            search_results = self.client.search(
                collection_name=self.COLLECTION_NAME,
                query_vector=query_embedding,
                query_filter=filters,
                limit=top_k,
                score_threshold=score_threshold
            )
            
            results = []
            for point in search_results:
                results.append({
                    "case_id": point.payload.get("case_id"),
                    "citation": point.payload.get("citation"),
                    "court": point.payload.get("court"),
                    "court_level": point.payload.get("court_level"),
                    "content_type": point.payload.get("content_type"),
                    "chunk_text": point.payload.get("chunk_text"),
                    "chunk_id": point.payload.get("chunk_id"),
                    "total_chunks": point.payload.get("total_chunks"),
                    "legal_concepts": point.payload.get("legal_concepts", []),
                    "similarity_score": point.score,
                    "metadata": point.payload
                })
            
            logger.debug(f"Retrieved {len(results)} case chunks from search")
            return results
            
        except Exception as e:
            logger.error(f"Case search failed: {e}")
            raise RuntimeError(f"Case search error: {e}")
    
    def get_cases_by_court_level(
        self,
        court_levels: List[int],
        date_range: Optional[tuple[str, str]] = None,
        legal_domain: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get cases filtered by court level and other criteria.
        
        Args:
            court_levels: List of court levels (1=Supreme, 2=High, 3=Lower)
            date_range: Tuple of (start_date, end_date) in ISO format
            legal_domain: Optional legal domain to filter by
            limit: Maximum results
        
        Returns:
            List of matching cases
        """
        try:
            filters = {}
            
            # Court level filter
            if court_levels:
                filters["court_level"] = {"in": court_levels}
            
            # Date range filter
            if date_range:
                start_date, end_date = date_range
                filters["date"] = {"range": {"gte": start_date, "lte": end_date}}
            
            # Legal domain filter
            if legal_domain:
                filters["legal_domain"] = {"equal": legal_domain}
            
            results = self.client.scroll(
                collection_name=self.COLLECTION_NAME,
                query_filter=filters if filters else None,
                limit=limit,
                with_payload=True,
                with_vectors=False
            )
            
            return [{"id": point.id, "metadata": point.payload} for point, _ in results[0]]
            
        except Exception as e:
            logger.error(f"Failed to get cases by court level: {e}")
            raise RuntimeError(f"Court level query failed: {e}")
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the case collection."""
        try:
            info = self.client.get_collection(self.COLLECTION_NAME)
            return {
                "collection_name": self.COLLECTION_NAME,
                "total_points": info.points_count,
                "vector_size": info.config.params.vectors.size,
                "status": str(info.status),
            }
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {}
    
    def delete_collection(self):
        """Delete the case collection (destructive operation)."""
        try:
            self.client.delete_collection(self.COLLECTION_NAME)
            logger.warning(f"Deleted collection: {self.COLLECTION_NAME}")
        except Exception as e:
            logger.error(f"Failed to delete collection: {e}")
            raise RuntimeError(f"Collection deletion failed: {e}")


# Helper function for creating chunking strategy
def get_chunk_config(chunk_type: str) -> Dict[str, int]:
    """
    Get recommended chunk sizes for semantic boundaries.
    
    Args:
        chunk_type: One of 'issue', 'ratio', 'statute', 'holding'
    
    Returns:
        Dict with 'min_tokens' and 'max_tokens'
    """
    configs = {
        "issue": {"min_tokens": 200, "max_tokens": 500},
        "ratio": {"min_tokens": 300, "max_tokens": 600},
        "statute": {"min_tokens": 150, "max_tokens": 400},
        "holding": {"min_tokens": 200, "max_tokens": 500},
    }
    
    return configs.get(chunk_type, {"min_tokens": 300, "max_tokens": 500})
