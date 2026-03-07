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

    _shared_qdrant_manager = None
    _shared_neo4j_schema = None
    _shared_embedding_service = None
    
    def __init__(self):
        """Initialize case retriever."""
        if CaseRetriever._shared_qdrant_manager is None:
            CaseRetriever._shared_qdrant_manager = QdrantCaseCollectionManager()

        if CaseRetriever._shared_neo4j_schema is None:
            CaseRetriever._shared_neo4j_schema = CaseGraphSchema()

        if CaseRetriever._shared_embedding_service is None:
            CaseRetriever._shared_embedding_service = InLegalBERTEmbeddingService()

        self.qdrant_manager = CaseRetriever._shared_qdrant_manager
        self.neo4j_schema = CaseRetriever._shared_neo4j_schema
        self.embedding_service = CaseRetriever._shared_embedding_service
    
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
            legal_domain: Optional legal domain filter (will be normalized to match Neo4j values)
        
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
            
            # Add legal domain filter if provided (normalize to match schema)
            if legal_domain:
                # Normalize: spaces/hyphens to underscores, lowercase
                normalized_domain = legal_domain.lower().replace(" ", "_").replace("-", "_")
                case_filters["legal_domain"] = normalized_domain
                logger.debug(f"Normalized legal_domain '{legal_domain}' -> '{normalized_domain}'")
            
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
        return self.embedding_service.embed_single_text(text).tolist()
    
    def _format_search_results(self, search_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format Qdrant search results into standard format."""
        formatted = []
        
        for result in search_results:
            formatted.append({
                "case_id": result.get("case_id"),
                "citation": result.get("citation"),
                "citation_normalized": result.get("citation_normalized"),
                "court": result.get("court"),
                "court_level": result.get("court_level"),
                "legal_domain": result.get("legal_domain"),  # Now include normalized domain
                "date": result.get("metadata", {}).get("date"),
                "chunk_text": result.get("chunk_text"),
                "content_type": result.get("content_type"),
                "legal_concepts": result.get("legal_concepts", []),
                "similarity_score": result.get("similarity_score"),
                "pdf_path": result.get("metadata", {}).get("pdf_path") or result.get("pdf_path"),
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
            
            # Combine results with ranking
            all_results = self._format_search_results(vector_results)
            
            # Track seen citations to avoid duplicates
            seen_citations = {r.get("citation") for r in all_results}
            
            # Add precedent info with enhanced metadata (now includes relationship type and confidence)
            precedent_count = 0
            for precedent in precedent_results:
                cite = precedent.get("citation")
                # Only add if not already in direct results
                if cite and cite not in seen_citations:
                    result_entry = {
                        "citation": cite,
                        "court": precedent.get("court"),
                        "date": precedent.get("date"),
                        "precedent_type": "discovered",
                        "relationship_type": precedent.get("relationship_type", "precedent"),  # Now tracks if precedent or appellate
                        "confidence": precedent.get("confidence", 0.7),  # Inferred relationship confidence
                        "distance": precedent.get("distance"),
                        "extraction_method": precedent.get("extraction_method", "graph_traversal")  # How relationship was found
                    }
                    all_results.append(result_entry)
                    precedent_count += 1
                    seen_citations.add(cite)
            
            retrieval_time = (time.time() - start_time) * 1000
            
            logger.info(f"Upper court retrieval: {len(vector_results)} direct results, {precedent_count} precedents + appellate in {retrieval_time:.2f}ms")
            
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
        return self.embedding_service.embed_single_text(text).tolist()
    
    def _discover_precedents(self, seed_cases: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Discover precedents and appellate relationships for seed cases using Neo4j graph traversal.
        
        Now leverages:
        - CITES relationships (precedent discovery - high confidence)
        - APPEALS_FROM relationships (appellate chain discovery)
        
        Args:
            seed_cases: Cases to find precedents/appellate relationships for
        
        Returns:
            List of discovered precedent cases with relationship metadata
        """
        precedents = {}  # Use dict to avoid duplicates; key=citation
        
        for case in seed_cases:
            case_id = case.get("case_id")
            if not case_id:
                continue
            
            try:
                # Query graph for precedents (CITES relationships)
                graph_precedents = self.neo4j_schema.query_case_precedents(case_id, depth=2)
                
                for precedent in graph_precedents:
                    key = precedent.get("citation", "")
                    if key and key not in precedents:
                        precedent_with_type = {**precedent, "relationship_type": "precedent"}
                        precedents[key] = precedent_with_type
                        logger.debug(f"Discovered precedent: {key} (distance: {precedent.get('distance', 'unknown')})")
            
            except Exception as e:
                logger.debug(f"Failed to discover precedents for {case_id}: {e}")
            
            try:
                # Query graph for appellate chain (APPEALS_FROM relationships)
                appellate_chain = self.neo4j_schema.query_appellate_chain(case_id)
                
                for appellate_case in appellate_chain:
                    key = appellate_case.get("citation", "")
                    if key and key not in precedents:
                        appellate_with_type = {**appellate_case, "relationship_type": "appellate"}
                        precedents[key] = appellate_with_type
                        logger.debug(f"Found appellate case: {key} (status: {appellate_case.get('status', 'unknown')})")
            
            except Exception as e:
                logger.debug(f"Failed to discover appellate chain for {case_id}: {e}")
        
        return list(precedents.values())
    
    def _format_search_results(self, search_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format search results."""
        formatted = []
        
        for result in search_results:
            formatted.append({
                "case_id": result.get("case_id"),
                "citation": result.get("citation"),
                "citation_normalized": result.get("citation_normalized"),
                "citation_aliases": result.get("citation_aliases", []),  # Support multi-citation cases
                "court": result.get("court"),
                "court_level": result.get("court_level"),
                "legal_domain": result.get("legal_domain"),
                "date": result.get("metadata", {}).get("date"),
                "metadata": result.get("metadata", {}),
                "chunk_text": result.get("chunk_text"),
                "content_type": result.get("content_type"),
                "legal_concepts": result.get("legal_concepts", []),
                "similarity_score": result.get("similarity_score"),
                "pdf_path": result.get("metadata", {}).get("pdf_path") or result.get("pdf_path"),
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
        confidence_threshold: float = 0.6,
        **kwargs
    ) -> RetrievalResult:
        """
        Retrieve appellate chain for a case with confidence filtering.
        
        Args:
            query: Case citation or ID (primary key)
            top_k: Not used for chain retrieval
            filters: Optional filters
            confidence_threshold: Only include edges with confidence >= this (default 0.6)
        
        Returns:
            RetrievalResult with appellate chain (high-confidence relationships only)
        """
        start_time = time.time()
        
        try:
            # Query Neo4j for appellate chain
            chain = self.neo4j_schema.query_appellate_chain(query)
            
            # Filter chain by confidence threshold to exclude low-confidence relationships
            if chain and isinstance(chain, list) and len(chain) > 0:
                # If chain items have confidence metadata, filter by threshold
                filtered_chain = [
                    case for case in chain
                    if case.get("confidence", 1.0) >= confidence_threshold or "confidence" not in case
                ]
                
                if len(filtered_chain) < len(chain):
                    logger.debug(
                        f"Filtered appellate chain: {len(chain)} cases -> {len(filtered_chain)} cases "
                        f"(confidence threshold: {confidence_threshold})"
                    )
                
                chain = filtered_chain
            
            # Enhance chain results with relationship metadata
            formatted_chain = []
            for i, case in enumerate(chain):
                formatted_case = {
                    "position_in_chain": i,  # Position in appellate sequence
                    "case_id": case.get("case_id"),
                    "citation": case.get("citation"),
                    "court": case.get("court"),
                    "date": case.get("date"),
                    "holding": case.get("holding"),
                    "decision": case.get("decision"),
                    "reversal_status": case.get("reversal_status"), # Direct or reverse
                    "confidence": case.get("confidence", 1.0),  # Relationship confidence
                    "extraction_method": case.get("extraction_method", "graph_traversal"),
                }
                formatted_chain.append(formatted_case)
            
            retrieval_time = (time.time() - start_time) * 1000
            
            logger.info(
                f"Appellate chain retrieval: {len(formatted_chain)} cases "
                f"(confidence >= {confidence_threshold}) in {retrieval_time:.2f}ms"
            )
            
            return RetrievalResult(
                query=query,
                results=formatted_chain,
                retrieval_type="appellate_chain",
                total_results=len(formatted_chain),
                retrieval_time_ms=retrieval_time,
                metadata={
                    "chain_depth": len(formatted_chain),
                    "confidence_threshold": confidence_threshold
                }
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

