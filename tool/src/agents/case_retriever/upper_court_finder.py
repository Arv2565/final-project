"""
Upper Court Case Finder Agent for Case Retrieval Module.

This agent searches for relevant precedents in Supreme Court and High Courts,
and detects appellate relationships.
"""

import logging
from typing import List, Dict, Any, Optional, Set
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from src.retrieval.case import UpperCourtCaseRetriever, CaseAppellateChainRetriever
from src.agents.case_retriever.models import (
    UpperCourtCaseResult, PrecedentInfo, AppellateChainLink, CaseInfo
)
from src.utils.court_hierarchy import is_upper_court_case, CourtLevel

logger = logging.getLogger(__name__)


class UpperCourtCaseFinderAgent:
    """Find precedents and appellate relationships in upper courts."""
    
    def __init__(self):
        """Initialize the agent."""
        self.retriever = UpperCourtCaseRetriever()
        self.chain_retriever = CaseAppellateChainRetriever()
    
    def __call__(
        self,
        lower_result: Optional[Dict[str, Any]] = None,
        state: Optional[Dict[str, Any]] = None,
        callbacks: Optional[List] = None
    ) -> Dict[str, Any]:
        """
        Execute case finding for upper courts and precedent discovery.
        
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
                user_query = lower_result.get("query", "")
                legal_concepts = lower_result.get("query_concepts", [])
                logger.info(f"UpperCourtCaseFinder: Finding precedents for {len(legal_concepts)} concepts")
            else:
                user_query = state.get("user_query", "") if state else ""
                legal_concepts = []
                logger.info(f"UpperCourtCaseFinder: Independent search mode")
            
            if not user_query:
                logger.warning("No query for upper court search")
                return {"upper_court_result": None}
            
            # Call retriever
            retrieval_result = self.retriever.retrieve(
                query=user_query,
                top_k=15,
                find_precedents=True
            )
            
            # Extract precedents from results
            precedents = []
            chain_results = []
            reversals_count = 0
            
            for result in retrieval_result.results:
                if result.get("result_type") == "direct":
                    # Direct match in upper court
                    precedent = PrecedentInfo(
                        citation=result.get("citation", ""),
                        court=result.get("court", ""),
                        court_level=result.get("court_level", 1),
                        date=result.get("date", ""),
                        decision=result.get("metadata", {}).get("decision"),
                        reversal_status=self._detect_reversal(result),
                        common_concepts=self._find_common_concepts(result, legal_concepts),
                        relevance_score=result.get("similarity_score", 0.0),
                        relationship_type="primary_precedent"
                    )
                    precedents.append(precedent)
                    
                    # Track reversals
                    if self._detect_reversal(result):
                        reversals_count += 1
                
                elif result.get("precedent_type") == "discovered":
                    # Graph-discovered precedent
                    precedent = PrecedentInfo(
                        citation=result.get("citation", ""),
                        court=result.get("court", ""),
                        court_level=1,  # Likely Supreme Court
                        date=result.get("date", ""),
                        reversal_status=result.get("status"),
                        relevance_score=result.get("distance", 3) / 3.0,  # Invert depth to score
                        relationship_type="cited_precedent"
                    )
                    precedents.append(precedent)
            
            # Attempt to recover appellate chains if we have lower court cases
            if lower_result:
                for lower_case in lower_result.get("cases", []):
                    try:
                        chain = self._build_appellate_chain(lower_case)
                        if chain:
                            chain_results.append(chain)
                    except Exception as e:
                        logger.debug(f"Failed to build chain for {lower_case.get('citation')}: {e}")
            
            upper_court_result = UpperCourtCaseResult(
                precedents=precedents,
                appellate_chains=chain_results,
                query_concepts=legal_concepts,
                search_query=user_query,
                retrieval_confidence=0.80,  # Could be computed
                total_precedents_available=len(precedents),
                reversals_detected=reversals_count
            )
            
            logger.info(
                f"UpperCourtCaseFinder: Found {len(precedents)} precedents, "
                f"{reversals_count} with reversals, {len(chain_results)} chains"
            )
            
            return {"upper_court_result": upper_court_result}
        
        except Exception as e:
            logger.error(f"UpperCourtCaseFinder error: {e}")
            raise RuntimeError(f"Upper court case finding failed: {e}")
    
    def _detect_reversal(self, result: Dict[str, Any]) -> Optional[str]:
        """Detect if result indicates a reversal."""
        decision = result.get("metadata", {}).get("decision", "").lower()
        
        if any(word in decision for word in ["reversed", "set aside", "quashed", "overturned"]):
            return "REVERSED"
        elif any(word in decision for word in ["upheld", "affirmed", "confirmed"]):
            return "UPHELD"
        elif any(word in decision for word in ["modified", "reduced", "enhanced"]):
            return "MODIFIED"
        elif any(word in decision for word in ["remanded", "remitted", "sent back"]):
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
