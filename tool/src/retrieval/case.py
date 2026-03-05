"""
Case-Specific Retrievers for Case Retrieval Module.

Implements retrievers for:
- LowerCourtCaseRetriever: Retrieve cases from lower court tier
- UpperCourtCaseRetriever: Retrieve cases from upper courts and precedents
- Hybrid case retriever combining both approaches
"""

import logging
import time
from typing import List, Dict, Any, Optional
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.retrieval.base import Retriever, VectorRetriever, RetrievalResult
from src.database.qdrant.case_collection import QdrantCaseCollectionManager
from src.database.neo4j.case_schema import CaseGraphSchema
from src.database.embeddings import InLegalBERTEmbeddingService
from src.utils.court_hierarchy import (
    CourtLevel, get_court_hierarchy_filter, is_lower_court_case, is_upper_court_case
)

logger = logging.getLogger(__name__)


class CaseRetriever(Retriever):
    """Base class for case-specific retrievers."""
    
    def __init__(self):
        """Initialize case retriever."""
        self.qdrant_manager = QdrantCaseCollectionManager()
        self.neo4j_schema = CaseGraphSchema()
        self.embedding_service = InLegalBERTEmbeddingService()
    
    def is_available(self) -> bool:
        """Check if both Qdrant and Neo4j are available."""
        try:
            # Check Qdrant
            stats = self.qdrant_manager.get_collection_stats()
            if not stats:
                return False
            
            # Check Neo4j by attempting a simple query
            self.neo4j_schema.query_case_precedents("dummy", depth=1)
            
            return True
        except Exception as e:
            logger.error(f"Availability check failed: {e}")
            return False
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check on case databases."""
        try:
            qdrant_stats = self.qdrant_manager.get_collection_stats()
            
            return {
                "status": "healthy" if self.is_available() else "unhealthy",
                "qdrant": qdrant_stats,
                "neo4j": "connected",
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }


class LowerCourtCaseRetriever(CaseRetriever, VectorRetriever):
    """
    Retrieves cases from lower court tier (District/Trial Courts).
    
    Uses vector search in Qdrant with court_level filter.
    """
    
    def retrieve(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        date_range: Optional[tuple[str, str]] = None,
        legal_domain: Optional[str] = None
    ) -> RetrievalResult:
        """
        Retrieve lower court cases matching the query.
        
        Args:
            query: Legal query/question
            top_k: Number of results to return
            filters: Optional additional filters
            date_range: Tuple of (start_date, end_date) in ISO format
            legal_domain: Optional legal domain filter
        
        Returns:
            RetrievalResult with lower court cases
        """
        start_time = time.time()
        
        try:
            # Embed the query
            query_embedding = self.get_embedding(query)
            
            # Build filters for lower courts only
            case_filters = filters or {}
            case_filters.update(get_court_hierarchy_filter([CourtLevel.LOWER_COURTS, CourtLevel.HIGH_COURT]))
            
            # Add date range filter if provided
            if date_range:
                case_filters["date_range"] = date_range
            
            # Add legal domain filter if provided
            if legal_domain:
                case_filters["legal_domain"] = legal_domain
            
            # Search Qdrant
            search_results = self.qdrant_manager.search_cases(
                query_embedding=query_embedding,
                top_k=top_k,
                filters=case_filters
            )
            
            # Format results
            formatted_results = self._format_search_results(search_results)
            
            retrieval_time = (time.time() - start_time) * 1000
            
            logger.info(f"Lower court retrieval: {len(formatted_results)} results in {retrieval_time:.2f}ms")
            
            return RetrievalResult(
                query=query,
                results=formatted_results,
                retrieval_type="lower_court_vector",
                total_results=len(formatted_results),
                retrieval_time_ms=retrieval_time,
                metadata={"court_levels": [1, 2, 3]}  # Lower courts include HC as appellate
            )
        
        except Exception as e:
            logger.error(f"Lower court retrieval failed: {e}")
            raise RuntimeError(f"Case retrieval failed: {e}")
    
    def get_embedding(self, text: str) -> List[float]:
        """Get embedding for text."""
        return self.embedding_service.embed_text(text)
    
    def _format_search_results(self, search_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format Qdrant search results into standard format."""
        formatted = []
        
        for result in search_results:
            formatted.append({
                "case_id": result.get("case_id"),
                "citation": result.get("citation"),
                "court": result.get("court"),
                "court_level": result.get("court_level"),
                "date": result.get("metadata", {}).get("date"),
                "chunk_text": result.get("chunk_text"),
                "content_type": result.get("content_type"),
                "legal_concepts": result.get("legal_concepts", []),
                "similarity_score": result.get("similarity_score"),
            })
        
        return formatted


class UpperCourtCaseRetriever(CaseRetriever, VectorRetriever):
    """
    Retrieves cases from upper court tier (Supreme Court, High Courts) and precedents.
    
    Combines vector search with graph traversal for precedent discovery.
    """
    
    def retrieve(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        find_precedents: bool = True,
        date_range: Optional[tuple[str, str]] = None
    ) -> RetrievalResult:
        """
        Retrieve upper court cases and precedents.
        
        Args:
            query: Legal query
            top_k: Number of results
            filters: Additional filters
            find_precedents: Whether to also find precedents
            date_range: Date range filter
        
        Returns:
            RetrievalResult with upper court cases and precedents
        """
        start_time = time.time()
        
        try:
            # Embed query
            query_embedding = self.get_embedding(query)
            
            # Build filters for upper courts
            case_filters = filters or {}
            case_filters.update(get_court_hierarchy_filter([CourtLevel.SUPREME_COURT, CourtLevel.HIGH_COURT]))
            
            # Add date range filter
            if date_range:
                case_filters["date_range"] = date_range
            
            # Vector search for direct matches
            vector_results = self.qdrant_manager.search_cases(
                query_embedding=query_embedding,
                top_k=top_k,
                filters=case_filters
            )
            
            # Graph-based precedent discovery
            precedent_results = []
            if find_precedents and vector_results:
                precedent_results = self._discover_precedents(vector_results[:5])  # Top 5 for precedent search
            
            # Combine results
            all_results = self._format_search_results(vector_results)
            
            # Add precedent info
            for precedent in precedent_results:
                all_results.append({
                    "citation": precedent.get("citation"),
                    "court": precedent.get("court"),
                    "date": precedent.get("date"),
                    "precedent_type": "discovered",
                    "distance": precedent.get("distance"),
                })
            
            retrieval_time = (time.time() - start_time) * 1000
            
            logger.info(f"Upper court retrieval: {len(vector_results)} direct results, {len(precedent_results)} precedents in {retrieval_time:.2f}ms")
            
            return RetrievalResult(
                query=query,
                results=all_results,
                retrieval_type="upper_court_hybrid",
                total_results=len(all_results),
                retrieval_time_ms=retrieval_time,
                metadata={
                    "direct_results": len(vector_results),
                    "precedent_results": len(precedent_results)
                }
            )
        
        except Exception as e:
            logger.error(f"Upper court retrieval failed: {e}")
            raise RuntimeError(f"Case retrieval failed: {e}")
    
    def get_embedding(self, text: str) -> List[float]:
        """Get embedding for text."""
        return self.embedding_service.embed_text(text)
    
    def _discover_precedents(self, seed_cases: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Discover precedents for seed cases using Neo4j graph traversal.
        
        Args:
            seed_cases: Cases to find precedents for
        
        Returns:
            List of discovered precedent cases
        """
        precedents = {}  # Use dict to avoid duplicates
        
        for case in seed_cases:
            case_id = case.get("case_id")
            if not case_id:
                continue
            
            try:
                # Query graph for precedents
                graph_precedents = self.neo4j_schema.query_case_precedents(case_id, depth=2)
                
                for precedent in graph_precedents:
                    key = precedent.get("citation", "")
                    if key and key not in precedents:
                        precedents[key] = precedent
            
            except Exception as e:
                logger.debug(f"Failed to discover precedents for {case_id}: {e}")
        
        return list(precedents.values())
    
    def _format_search_results(self, search_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format search results."""
        formatted = []
        
        for result in search_results:
            formatted.append({
                "case_id": result.get("case_id"),
                "citation": result.get("citation"),
                "court": result.get("court"),
                "court_level": result.get("court_level"),
                "date": result.get("metadata", {}).get("date"),
                "chunk_text": result.get("chunk_text"),
                "content_type": result.get("content_type"),
                "legal_concepts": result.get("legal_concepts", []),
                "similarity_score": result.get("similarity_score"),
                "result_type": "direct",
            })
        
        return formatted


class CaseAppellateChainRetriever(CaseRetriever):
    """
    Retrieves complete appellate chains for a case.
    
    Uses Neo4j graph to trace case through multiple court levels.
    """
    
    def retrieve(
        self,
        query: str,  # Case citation or ID
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> RetrievalResult:
        """
        Retrieve appellate chain for a case.
        
        Args:
            query: Case citation or ID (primary key)
            top_k: Not used for chain retrieval
            filters: Optional filters
        
        Returns:
            RetrievalResult with appellate chain
        """
        start_time = time.time()
        
        try:
            # Query Neo4j for appellate chain
            chain = self.neo4j_schema.query_appellate_chain(query)
            
            retrieval_time = (time.time() - start_time) * 1000
            
            logger.info(f"Appellate chain retrieval: {len(chain)} cases in {retrieval_time:.2f}ms")
            
            return RetrievalResult(
                query=query,
                results=chain,
                retrieval_type="appellate_chain",
                total_results=len(chain),
                retrieval_time_ms=retrieval_time,
                metadata={"chain_depth": len(chain)}
            )
        
        except Exception as e:
            logger.error(f"Appellate chain retrieval failed: {e}")
            raise RuntimeError(f"Appellate chain retrieval failed: {e}")
    
    def is_available(self) -> bool:
        """Check if Neo4j is available."""
        try:
            self.neo4j_schema.query_case_precedents("dummy", depth=1)
            return True
        except Exception:
            return False
    
    def health_check(self) -> Dict[str, Any]:
        """Health check for graph database."""
        return {
            "status": "healthy" if self.is_available() else "unhealthy",
            "database": "neo4j"
        }


# Helper function for creating case-specific filters

