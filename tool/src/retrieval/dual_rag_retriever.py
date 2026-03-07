"""
Dual-RAG Retriever for Parallel Naive and Graph-Based Retrieval.

Combines naive vector search with graph-based retrieval,
running both in parallel and merging results ranked by relevance.
Returns full case JSON for each result using citation lookup.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
import time

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.retrieval.case import LowerCourtCaseRetriever, UpperCourtCaseRetriever
from src.services.case_json_loader import get_case_json_loader

logger = logging.getLogger(__name__)


class DualRAGRetriever:
    """
    Combines naive vector search and graph-based retrieval in parallel.
    
    For each court level:
    1. Runs naive RAG (pure vector search with inLegalBERT)
    2. Runs graph RAG (entity/relationship search with OpenAI embeddings)
    3. Merges top results (2 from each strategy)
    4. De-duplicates and ranks by relevance
    5. Looks up full case JSON by citation
    6. Returns enriched results with complete case data
    """
    
    def __init__(self):
        """Initialize retrievers."""
        self.lower_court_retriever = LowerCourtCaseRetriever()
        self.upper_court_retriever = UpperCourtCaseRetriever()
        self.case_json_loader = get_case_json_loader()
        
        logger.info("DualRAGRetriever initialized with naive and graph retrievers")
    
    def retrieve_lower_court_with_json(
        self,
        query: str,
        top_k: int = 4,
        filters: Optional[Dict[str, Any]] = None,
        date_range: Optional[Tuple[str, str]] = None,
        legal_domain: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve lower court cases using parallel naive + graph RAG.
        
        Args:
            query: Legal query/question
            top_k: Target total results (usually 4, from 2 naive + 2 graph)
            filters: Optional retrieval filters
            date_range: Optional date range tuple
            legal_domain: Optional legal domain filter
        
        Returns:
            List of dicts containing:
            - full_case_json: Complete case data from casefiles.json
            - citation: Case citation
            - relevance_score: Merged relevance score (0-1)
            - retrieval_method: "naive"|"graph"|"hybrid"
            - additional metadata
        
        Raises:
            Exception: If both retrievers fail
        """
        logger.info(f"DualRAGRetriever: Retrieving lower court cases for query: {query[:80]}...")
        
        # Run both retrievers in parallel
        naive_results = self._run_naive_retrieval(
            query=query,
            top_k=2,  # Get 2 from naive
            court_level="lower",
            filters=filters,
            date_range=date_range,
            legal_domain=legal_domain
        )
        
        graph_results = self._run_graph_retrieval(
            query=query,
            top_k=2,  # Get 2 from graph
            court_level="lower",
            filters=filters
        )
        
        # Merge and lookup
        merged_results = self._merge_and_rank_results(naive_results, graph_results)
        
        # Keep only top_k results
        merged_results = merged_results[:top_k]
        
        # Lookup full case JSON for each result
        enriched_results = self._enrich_with_case_json(merged_results)
        
        logger.info(f"DualRAGRetriever: Retrieved {len(enriched_results)} lower court cases")
        return enriched_results
    
    def retrieve_upper_court_with_json(
        self,
        query: str,
        top_k: int = 4,
        filters: Optional[Dict[str, Any]] = None,
        date_range: Optional[Tuple[str, str]] = None,
        legal_domain: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve upper court/precedent cases using parallel naive + graph RAG.
        
        Args:
            query: Legal query/question
            top_k: Target total results
            filters: Optional retrieval filters
            date_range: Optional date range
            legal_domain: Optional legal domain filter
        
        Returns:
            List of enriched case results with full JSON data
        """
        logger.info(f"DualRAGRetriever: Retrieving upper court cases for query: {query[:80]}...")
        
        # Run both retrievers in parallel
        naive_results = self._run_naive_retrieval(
            query=query,
            top_k=2,
            court_level="upper",
            filters=filters,
            date_range=date_range,
            legal_domain=legal_domain
        )
        
        graph_results = self._run_graph_retrieval(
            query=query,
            top_k=2,
            court_level="upper",
            filters=filters
        )
        
        # Merge and lookup
        merged_results = self._merge_and_rank_results(naive_results, graph_results)
        merged_results = merged_results[:top_k]
        
        enriched_results = self._enrich_with_case_json(merged_results)
        
        logger.info(f"DualRAGRetriever: Retrieved {len(enriched_results)} upper court cases")
        return enriched_results
    
    def _run_naive_retrieval(
        self,
        query: str,
        top_k: int,
        court_level: str,
        filters: Optional[Dict[str, Any]] = None,
        date_range: Optional[Tuple[str, str]] = None,
        legal_domain: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Run naive vector search retrieval."""
        try:
            logger.debug(f"Running naive RAG for {court_level} court with top_k={top_k}")
            start_time = time.time()
            
            if court_level == "lower":
                result = self.lower_court_retriever.retrieve(
                    query=query,
                    top_k=top_k,
                    filters=filters,
                    date_range=date_range,
                    legal_domain=legal_domain
                )
            else:
                result = self.upper_court_retriever.retrieve(
                    query=query,
                    top_k=top_k,
                    filters=filters,
                    date_range=date_range,
                    legal_domain=legal_domain
                )
            
            elapsed = (time.time() - start_time) * 1000
            results = [
                {
                    **r,
                    "retrieval_method": "naive_rag"
                }
                for r in result.results
            ]
            logger.debug(f"Naive retrieval completed in {elapsed:.2f}ms, returned {len(results)} results")
            return results
        
        except Exception as e:
            logger.error(f"Naive retrieval failed for {court_level} court: {e}")
            return []
    
    def _run_graph_retrieval(
        self,
        query: str,
        top_k: int,
        court_level: str,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Run graph-augmented retrieval using case retrievers."""
        try:
            logger.debug(f"Running graph RAG for {court_level} court with top_k={top_k}")
            start_time = time.time()

            if court_level == "upper":
                result = self.upper_court_retriever.retrieve(
                    query=query,
                    top_k=top_k,
                    filters=filters,
                    find_precedents=True,
                )
            else:
                # Lower court graph path falls back to case-aware retrieval,
                # while still tagging method separately for downstream blending.
                result = self.lower_court_retriever.retrieve(
                    query=query,
                    top_k=top_k,
                    filters=filters,
                )
            
            elapsed = (time.time() - start_time) * 1000
            results = [
                {
                    **r,
                    "retrieval_method": "graph_rag"
                }
                for r in result.results
            ]
            logger.debug(f"Graph retrieval completed in {elapsed:.2f}ms, returned {len(results)} results")
            return results
        
        except Exception as e:
            logger.error(f"Graph retrieval failed for {court_level} court: {e}")
            return []
    
    def _merge_and_rank_results(
        self,
        naive_results: List[Dict[str, Any]],
        graph_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Merge naive and graph results, de-duplicate by case_id, and rank by relevance.
        
        Args:
            naive_results: Results from naive vector search
            graph_results: Results from graph-based search
        
        Returns:
            Merged and ranked results list
        """
        try:
            # Combine results
            all_results = naive_results + graph_results
            
            if not all_results:
                logger.warning("No results from either retriever to merge")
                return []
            
            # De-duplicate by case_id or citation (prefer citation as it's more unique)
            seen = {}
            for result in all_results:
                # Use citation as primary key (more unique across databases)
                citation = result.get("citation") or result.get("case_id", "unknown")
                
                if citation not in seen:
                    seen[citation] = result
                else:
                    # If duplicate, keep the one with higher score
                    existing_score = seen[citation].get("similarity_score", 0)
                    new_score = result.get("similarity_score", 0)
                    if new_score > existing_score:
                        seen[citation] = result
            
            # Rank by relevance score
            merged = sorted(
                seen.values(),
                key=lambda x: x.get("similarity_score", 0),
                reverse=True
            )
            
            logger.info(f"Merged {len(all_results)} results into {len(merged)} unique results")
            return merged
        
        except Exception as e:
            logger.error(f"Error merging results: {e}")
            return naive_results + graph_results
    
    def _enrich_with_case_json(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Look up full case JSON for each result by citation.
        
        Args:
            results: List of retrieval results with citations
        
        Returns:
            Enriched results with full case JSON data
        """
        enriched = []
        
        for result in results:
            try:
                citation = result.get("citation")
                if not citation:
                    logger.warning(f"Result missing citation, skipping enrichment: {result}")
                    continue
                
                # Load full case JSON from casefiles.json
                full_case_json = self.case_json_loader.load_case_by_citation(citation)
                
                if full_case_json:
                    enriched_result = {
                        **result,
                        "full_case_json": full_case_json,
                        "case_lookup_status": "found"
                    }
                    enriched.append(enriched_result)
                    logger.debug(f"Enriched result with full case JSON: {citation}")
                else:
                    logger.warning(f"Full case JSON not found for citation: {citation}")
                    # Still include result but mark as incomplete
                    enriched_result = {
                        **result,
                        "full_case_json": None,
                        "case_lookup_status": "not_found"
                    }
                    enriched.append(enriched_result)
            
            except Exception as e:
                logger.error(f"Error enriching result: {e}")
                # Include result without enrichment
                enriched.append({**result, "case_lookup_status": "error"})
        
        logger.info(f"Enriched {len(enriched)} results with case JSON from casefiles.json")
        return enriched
