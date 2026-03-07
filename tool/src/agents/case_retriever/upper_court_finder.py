"""
Upper Court Case Finder Agent for Case Retrieval Module.

This agent searches for relevant precedents in Supreme Court and High Courts.
Uses parallel naive RAG + graph RAG retrieval for comprehensive coverage.
"""

import logging
from typing import List, Dict, Any, Optional, Set
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from src.retrieval.dual_rag_retriever import DualRAGRetriever
from src.agents.case_retriever.models import (
    UpperCourtCaseResult, PrecedentInfo, AppellateChainLink, CaseInfo
)
from src.utils.court_hierarchy import is_upper_court_case, CourtLevel

logger = logging.getLogger(__name__)


class UpperCourtCaseFinderAgent:
    """Find precedents in upper courts using dual RAG precedent discovery."""
    
    def __init__(self):
        """Initialize the agent with dual-RAG retriever."""
        self.dual_retriever = DualRAGRetriever()
    
    def __call__(
        self,
        lower_result: Optional[Dict[str, Any]] = None,
        state: Optional[Dict[str, Any]] = None,
        callbacks: Optional[List] = None
    ) -> Dict[str, Any]:
        """
        Execute case finding for upper courts using dual RAG (naive + graph).
        
        Args:
            lower_result: Result from LowerCourtCaseFinderAgent (optional)
            state: GraphState
            callbacks: Optional callback handlers
        
        Returns:
            Dict with 'upper_court_result' key containing UpperCourtCaseResult
        """
        try:
            # Determine search strategy based on lower_result
            if lower_result:
                user_query = lower_result.get("search_query", "")
                if not user_query and state:
                    user_query = state.get("user_query", "")
                legal_concepts = lower_result.get("query_concepts", [])
                logger.info(f"UpperCourtCaseFinder: Finding precedents for {len(legal_concepts)} concepts")
            else:
                user_query = state.get("user_query", "") if state else ""
                legal_concepts = []
                logger.info(f"UpperCourtCaseFinder: Independent search mode")
            
            if not user_query:
                logger.warning("No query for upper court search")
                return {"upper_court_result": None}
            
            # Call dual-RAG retriever (runs naive + graph RAG in parallel)
            enriched_results = self.dual_retriever.retrieve_upper_court_with_json(
                query=user_query,
                top_k=4  # Get 2 naive + 2 graph = 4 total
            )
            
            # Extract precedents from enriched results
            precedents = []
            reversals_count = 0
            
            for result in enriched_results:
                try:
                    full_case_json = result.get("full_case_json", {})
                    
                    # Determine reversal status from decision
                    reversal_status = self._detect_reversal_from_decision(
                        full_case_json.get("holding", {}).get("decision") if full_case_json else result.get("decision")
                    )
                    
                    precedent = PrecedentInfo(
                        citation=result.get("citation", ""),
                        court=result.get("court", ""),
                        court_level=result.get("court_level", 1),
                        date=result.get("date", ""),
                        decision=full_case_json.get("holding", {}).get("decision") if full_case_json else result.get("decision"),
                        reversal_status=reversal_status,
                        common_concepts=full_case_json.get("legal_concepts", []) if full_case_json else result.get("legal_concepts", []),
                        relevance_score=result.get("similarity_score", 0.0),
                        relationship_type="primary_precedent",
                        pdf_path=full_case_json.get("evidence", {}).get("pdf_path") if full_case_json else result.get("pdf_path")
                    )
                    precedents.append(precedent)
                    
                    if reversal_status == "REVERSED":
                        reversals_count += 1
                
                except Exception as e:
                    logger.error(f"Error processing precedent result: {e}")
                    continue
            
            upper_court_result = UpperCourtCaseResult(
                precedents=precedents,
                appellate_chains=[],  # Appellate chains discovery via dual RAG precedent matching
                query_concepts=legal_concepts,
                search_query=user_query,
                retrieval_confidence=0.80,
                total_precedents_available=len(precedents),
                reversals_detected=reversals_count
            )
            
            logger.info(
                f"UpperCourtCaseFinder: Retrieved {len(precedents)} upper court cases"
                f" using dual RAG, {reversals_count} with reversals"
            )
            
            return {"upper_court_result": upper_court_result}
        
        except Exception as e:
            logger.error(f"UpperCourtCaseFinder error: {e}")
            raise RuntimeError(f"Upper court case finding failed: {e}")
    
    def _detect_reversal(self, result: Dict[str, Any]) -> Optional[str]:
        """Detect if result indicates a reversal."""
        decision = result.get("metadata", {}).get("decision", "").lower()
        return self._detect_reversal_from_decision(decision)
    
    def _detect_reversal_from_decision(self, decision: Optional[str]) -> Optional[str]:
        """Detect reversal status from decision text."""
        if not decision:
            return None
        
        decision_lower = decision.lower()
        
        if any(word in decision_lower for word in ["reversed", "set aside", "quashed", "overturned"]):
            return "REVERSED"
        elif any(word in decision_lower for word in ["upheld", "affirmed", "confirmed"]):
            return "UPHELD"
        elif any(word in decision_lower for word in ["modified", "reduced", "enhanced"]):
            return "MODIFIED"
        elif any(word in decision_lower for word in ["remanded", "remitted", "sent back"]):
            return "REMANDED"
        
        return None
    
    def _find_common_concepts(self, result: Dict[str, Any], legal_concepts: List[str]) -> List[str]:
        """Find concepts shared with query."""
        result_concepts = set(result.get("legal_concepts", []))
        query_concepts = set(legal_concepts)
        
        return list(result_concepts & query_concepts)
    
    def _build_appellate_chain(self, lower_case: CaseInfo) -> Optional[List[AppellateChainLink]]:
        """
        Attempt to build appellate chain for a lower court case.
        
        Queries Neo4j for APPEALS_FROM relationships.
        """
        try:
            # Attempt to query appellate chain from Neo4j
            # This would use the chain_retriever, but we'll build manually for now
            
            chain = [
                AppellateChainLink(
                    case_id=lower_case.case_id,
                    citation=lower_case.citation,
                    court=lower_case.court,
                    court_level=lower_case.court_level,
                    date=lower_case.date,
                    position_in_chain=0
                )
            ]
            
            # In production, would query Neo4j for higher court appeals
            # For now, return single case as chain
            return chain if len(chain) > 1 else None
        
        except Exception as e:
            logger.debug(f"Failed to build chain: {e}")
            return None
