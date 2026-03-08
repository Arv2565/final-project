"""
Upper Court Case Finder Agent for Case Retrieval Module.

This agent uses LLM to select maximum 2 most relevant case citations
from higher_case.json based on user query.
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


class UpperCourtCaseFinderAgent:
    """Find precedents in upper courts using LLM citation selection."""
    
    def __init__(self):
        """Initialize the agent with LLM for citation selection."""
        self.llm = get_agent_llm(
            model_type="research",
            output_schema=CitationSelectionResult
        )
        # Load higher_case.json
        data_path = Path(__file__).parent.parent.parent.parent / "data" / "higher_case.json"
        with open(data_path, 'r', encoding='utf-8') as f:
            self.higher_cases = json.load(f)
        logger.info(f"Loaded {len(self.higher_cases)} higher court cases from JSON")
    
    def __call__(
        self,
        lower_result: Optional[Dict[str, Any]] = None,
        state: Optional[Dict[str, Any]] = None,
        callbacks: Optional[List] = None
    ) -> Dict[str, Any]:
        """
        Execute case finding for upper courts using LLM citation selection.
        
        Args:
            lower_result: Result from LowerCourtCaseFinderAgent (optional)
            state: GraphState
            callbacks: Optional callback handlers
        
        Returns:
            Dict with 'upper_citations' key containing list of max 2 citations
        """
        try:
            # Extract user query from state
            user_query = state.get("user_query", "") if state else ""
            
            if not user_query:
                logger.warning("No query for upper court search")
                return {"upper_citations": []}
            
            logger.info(f"UpperCourtCaseFinder: Processing query: {user_query[:100]}...")
            
            # Prepare prompt for LLM
            prompt = (
                "You are a legal case selection expert. Analyze the user query and select the maximum 2 most relevant case citations from the provided higher court cases (Supreme Court and High Courts).\n"
                "Consider the following when selecting cases:\n"
                "- Legal concepts and constitutional principles\n"
                "- Precedential value and binding nature\n"
                "- Landmark status and legal doctrines\n"
                "- Relevance to the query's legal issues\n\n"
                f"User Query: {user_query}\n\n"
                f"Available Cases (JSON array):\n{json.dumps(self.higher_cases, indent=2, ensure_ascii=False)}\n\n"
                "Select maximum 2 most relevant citations and explain your reasoning."
            )
            
            # Call LLM for citation selection
            logger.info("UpperCourtCaseFinder: Calling LLM for citation selection...")
            result: CitationSelectionResult = self.llm.invoke(prompt)
            
            # Ensure max 2 citations
            selected_citations = result.selected_citations[:2]
            
            logger.info(
                f"UpperCourtCaseFinder: Selected {len(selected_citations)} citations: {selected_citations}\n"
                f"Reasoning: {result.reasoning}"
            )
            
            return {"upper_citations": selected_citations}
        
        except Exception as e:
            logger.error(f"UpperCourtCaseFinder error: {e}", exc_info=True)
            # Return empty list on error instead of raising
            return {"upper_citations": []}
