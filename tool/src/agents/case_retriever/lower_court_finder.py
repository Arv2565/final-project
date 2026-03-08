"""
Lower Court Case Finder Agent for Case Retrieval Module.

This agent uses LLM to select maximum 2 most relevant case citations
from lower_case.json based on user query.
"""

import logging
import json
from typing import List, Dict, Any, Optional
import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from src.agents.agent_llm_helper import get_agent_llm
from src.agents.case_retriever.models import CitationSelectionResult

logger = logging.getLogger(__name__)


class LowerCourtCaseFinderAgent:
    """Find relevant cases from lower/district courts using LLM citation selection."""
    
    def __init__(self):
        """Initialize the agent with LLM for citation selection."""
        self.llm = get_agent_llm(
            model_type="research",
            output_schema=CitationSelectionResult
        )
        # Load lower_case.json
        data_path = Path(__file__).parent.parent.parent.parent / "data" / "lower_case.json"
        with open(data_path, 'r', encoding='utf-8') as f:
            self.lower_cases = json.load(f)
        logger.info(f"Loaded {len(self.lower_cases)} lower court cases from JSON")
    
    def __call__(self, state: Dict[str, Any], callbacks: Optional[List] = None) -> Dict[str, Any]:
        """
        Execute case finding for lower courts using LLM citation selection.
        
        Args:
            state: GraphState containing user_query and other context
            callbacks: Optional callback handlers for logging
        
        Returns:
            Dict with 'lower_citations' key containing list of max 2 citations
        """
        try:
            # Extract query from state
            user_query = state.get("user_query", "")
            if not user_query:
                logger.warning("No user query provided")
                return {"lower_citations": []}
            
            logger.info(f"LowerCourtCaseFinder: Processing query: {user_query[:100]}...")
            
            # Prepare prompt for LLM
            prompt = (
                "You are a legal case selection expert. Analyze the user query and select the maximum 2 most relevant case citations from the provided lower court cases.\n"
                "Consider the following when selecting cases:\n"
                "- Legal concepts and issues mentioned in the query\n"
                "- Factual similarity\n"
                "- Jurisdiction and court level\n"
                "- Year and relevance of precedent\n\n"
                f"User Query: {user_query}\n\n"
                f"Available Cases (JSON array):\n{json.dumps(self.lower_cases, indent=2, ensure_ascii=False)}\n\n"
                "Select maximum 2 most relevant citations and explain your reasoning."
            )
            
            # Call LLM for citation selection
            logger.info("LowerCourtCaseFinder: Calling LLM for citation selection...")
            result: CitationSelectionResult = self.llm.invoke(prompt)
            
            # Ensure max 2 citations
            selected_citations = result.selected_citations[:2]
            
            logger.info(
                f"LowerCourtCaseFinder: Selected {len(selected_citations)} citations: {selected_citations}\n"
                f"Reasoning: {result.reasoning}"
            )
            
            return {"lower_citations": selected_citations}
        
        except Exception as e:
            logger.error(f"LowerCourtCaseFinder error: {e}", exc_info=True)
            # Return empty list on error instead of raising
            return {"lower_citations": []}
