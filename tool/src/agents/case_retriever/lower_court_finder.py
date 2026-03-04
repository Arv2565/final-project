"""
Lower Court Case Finder Agent for Case Retrieval Module.

This agent searches for relevant cases in district/lower courts tier.
"""

import logging
from typing import List, Dict, Any, Optional
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from src.retrieval.case import LowerCourtCaseRetriever
from src.agents.case_retriever.models import LowerCourtCaseResult, CaseInfo, QueryContext
from src.utils.court_hierarchy import is_lower_court_case, CourtLevel

logger = logging.getLogger(__name__)


class LowerCourtCaseFinderAgent:
    """Find relevant cases from lower/district courts."""
    
    def __init__(self):
        """Initialize the agent."""
        self.retriever = LowerCourtCaseRetriever()
    
    def __call__(self, state: Dict[str, Any], callbacks: Optional[List] = None) -> Dict[str, Any]:
        """
        Execute case finding for lower courts.
        
        Args:
            state: GraphState containing user_query and other context
            callbacks: Optional callback handlers for logging
        
        Returns:
            Dict with 'lower_court_result' key containing LowerCourtCaseResult
        """
        try:
            # Extract query from state
            user_query = state.get("user_query", "")
            if not user_query:
                logger.warning("No user query provided")
                return {"lower_court_result": None}
            
            logger.info(f"LowerCourtCaseFinder: Processing query: {user_query[:100]}...")
            
            # Extract context from query (simplified - in production use LLM)
            query_context = self._extract_query_context(user_query)
            
            # Call retriever
            retrieval_result = self.retriever.retrieve(
                query=user_query,
                top_k=10,
                legal_domain=query_context.legal_domains[0] if query_context.legal_domains else None,
                date_range=query_context.date_constraints
            )
            
            # Convert to LowerCourtCaseResult
            cases = []
            for result in retrieval_result.results:
                cases.append(CaseInfo(
                    case_id=result.get("case_id", ""),
                    citation=result.get("citation", ""),
                    court=result.get("court", ""),
                    court_level=result.get("court_level", 3),
                    date=result.get("date", ""),
                    decision=result.get("metadata", {}).get("decision"),
                    legal_concepts=result.get("legal_concepts", []),
                    statutes_mentioned=result.get("metadata", {}).get("statutes_mentioned", []),
                    content_preview=result.get("chunk_text", "")[:200] if result.get("chunk_text") else None,
                    similarity_score=result.get("similarity_score")
                ))
            
            lower_court_result = LowerCourtCaseResult(
                cases=cases,
                query_concepts=query_context.legal_concepts,
                search_query=user_query,
                retrieval_confidence=0.85,  # Could be computed from scores
                total_cases_available=len(cases),
                filters_applied={
                    "court_levels": [2, 3],  # HC and Lower courts
                    "legal_domain": query_context.legal_domains[0] if query_context.legal_domains else None
                }
            )
            
            logger.info(f"LowerCourtCaseFinder: Found {len(cases)} cases")
            
            return {"lower_court_result": lower_court_result}
        
        except Exception as e:
            logger.error(f"LowerCourtCaseFinder error: {e}")
            raise RuntimeError(f"Lower court case finding failed: {e}")
    
    def _extract_query_context(self, query: str) -> QueryContext:
        """
        Extract relevant context from user query.
        
        In production, this would use an LLM. For now, simple keyword extraction.
        """
        # Simple keyword extraction (could be enhanced with LLM)
        legal_domains = []
        if any(word in query.lower() for word in ["criminal", "crime", "offence", "section 302", "ipc"]):
            legal_domains.append("criminal_law")
        elif any(word in query.lower() for word in ["civil", "contract", "tort", "negligence"]):
            legal_domains.append("civil_law")
        elif any(word in query.lower() for word in ["constitution", "article", "fundamental"]):
            legal_domains.append("constitutional_law")
        elif any(word in query.lower() for word in ["service", "employment", "promotion", "dismissal"]):
            legal_domains.append("service_law")
        else:
            legal_domains.append("general_law")
        
        # Extract concepts
        concepts = []
        keywords = {
            "bail": "bail", "custody": "custodial_torture", "evidence": "evidence_admissibility",
            "witness": "witness_credibility", "injury": "personal_injury", "contract": "contract_breach",
            "ownership": "property_rights", "liberty": "personal_liberty", "article 21": "article_21"
        }
        
        for keyword, concept in keywords.items():
            if keyword in query.lower():
                concepts.append(concept)
        
        return QueryContext(
            original_query=query,
            legal_concepts=concepts if concepts else ["general_legal_issue"],
            statutes_mentioned=[],
            legal_domains=legal_domains,
            court_levels_preferred=[2, 3],  # HC and Lower courts
            date_constraints=None,
            reversal_indicators="overturn" in query.lower() or "reverse" in query.lower()
        )
