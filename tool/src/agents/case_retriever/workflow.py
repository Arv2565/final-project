"""
Case Retriever Workflow Orchestration.

This module orchestrates the 3-agent system for case retrieval:
1. LowerCourtCaseFinderAgent - discovers lower court cases
2. UpperCourtCaseFinderAgent - discovers precedents and appellate chains
3. CaseComparativeAnalyzerAgent - generates final markdown synthesis
"""

import logging
from typing import Dict, Any, List, Optional
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.agents.case_retriever.lower_court_finder import LowerCourtCaseFinderAgent
from src.agents.case_retriever.upper_court_finder import UpperCourtCaseFinderAgent
from src.agents.case_retriever.comparative_analyzer import CaseComparativeAnalyzerAgent
from src.agents.case_retriever.models import CaseRetrieverState

logger = logging.getLogger(__name__)


class CaseRetrieverWorkflow:
    """
    Orchestrates the case retrieval workflow.
    
    Executes:
    1. Lower court case finding (parallel independence)
    2. Upper court case finding (parallel independence)
    3. LLM synthesis (sequential after both finders)
    
    All agents work with accumulating state passed through the workflow.
    """
    
    def __init__(self):
        """Initialize workflow agents."""
        self.lower_court_finder = LowerCourtCaseFinderAgent()
        self.upper_court_finder = UpperCourtCaseFinderAgent()
        self.analyzer = CaseComparativeAnalyzerAgent()
        
        logger.info("CaseRetrieverWorkflow initialized with 3 agents")
    
    def __call__(
        self,
        state: Dict[str, Any],
        callbacks: Optional[List] = None
    ) -> Dict[str, Any]:
        """
        Execute the case retrieval workflow.
        
        Orchestrates the 3-agent system in parallel where possible.
        
        Args:
            state: GraphState containing user_query and other context
            callbacks: Optional callback handlers for Langfuse tracking
        
        Returns:
            Dict with 'case_retriever_state' containing complete workflow results
        
        Raises:
            RuntimeError: If any agent fails
        """
        try:
            # Extract query from state
            user_query = state.get("user_query", "")
            if not user_query:
                logger.error("No user query provided to workflow")
                raise ValueError("user_query is required in state")
            
            logger.info(f"CaseRetrieverWorkflow: Starting workflow for query: {user_query[:80]}...")
            
            # ==================================================================
            # STAGE 1: Parallel Execution of Lower and Upper Court Finders
            # ==================================================================
            logger.info("CaseRetrieverWorkflow: Stage 1 - Executing finders in parallel")
            logger.info("CaseRetrieverWorkflow: 🔎 Searching lower court cases...")
            
            # Execute lower court finder - returns list of citations
            lower_citations = []
            lower_court_error = None
            try:
                lower_result_dict = self.lower_court_finder(state, callbacks=callbacks)
                lower_citations = lower_result_dict.get("lower_citations", [])
                logger.info(f"Lower court finder completed successfully: {len(lower_citations)} citations")
            except Exception as e:
                lower_court_error = e
                logger.error(f"Lower court finder failed: {e}")
            
            # Execute upper court finder - returns list of citations
            logger.info("CaseRetrieverWorkflow: 📚 Analyzing precedents and appellate chains...")
            upper_citations = []
            upper_court_error = None
            try:
                upper_result_dict = self.upper_court_finder(
                    lower_result=None,  # No longer needed
                    state=state,
                    callbacks=callbacks
                )
                upper_citations = upper_result_dict.get("upper_citations", [])
                logger.info(f"Upper court finder completed successfully: {len(upper_citations)} citations")
            except Exception as e:
                upper_court_error = e
                logger.error(f"Upper court finder failed: {e}")
            
            # Check if at least one finder succeeded
            if not lower_citations and not upper_citations:
                error_msg = "Both finders failed to return citations"
                if lower_court_error:
                    error_msg += f": Lower - {lower_court_error}"
                if upper_court_error:
                    error_msg += f"; Upper - {upper_court_error}"
                raise RuntimeError(error_msg)
            
            # ==================================================================
            # STAGE 2: LLM Synthesis (Sequential on Citation Results)
            # ==================================================================
            logger.info("CaseRetrieverWorkflow: Stage 2 - Running comparative analyzer")
            logger.info(f"CaseRetrieverWorkflow: ⚖️ Analyzing {len(lower_citations)} lower + {len(upper_citations)} upper citations...")
            
            analysis_result = None
            analysis_error = None
            
            try:
                analyzer_result_dict = self.analyzer(
                    lower_citations=lower_citations,
                    upper_citations=upper_citations,
                    state=state,
                    callbacks=callbacks
                )
                analysis_result = analyzer_result_dict.get("analysis_result")
                logger.info("Comparative analyzer completed successfully")
            except Exception as e:
                analysis_error = e
                logger.error(f"Comparative analyzer failed: {e}")
            
            # ==================================================================
            # STAGE 3: Accumulate Results into State
            # ==================================================================
            logger.info("CaseRetrieverWorkflow: Stage 3 - Accumulating results")
            
            case_retriever_state = {
                "lower_court_citations": lower_citations,
                "upper_court_citations": upper_citations,
                "case_analysis": analysis_result.dict() if analysis_result else None,
                "workflow_status": "completed" if (lower_citations or upper_citations) else "failed",
                "errors": {
                    "lower_court_finder": str(lower_court_error) if lower_court_error else None,
                    "upper_court_finder": str(upper_court_error) if upper_court_error else None,
                    "comparative_analyzer": str(analysis_error) if analysis_error else None,
                }
            }
            
            # ==================================================================
            # FINAL: Return Results
            # ==================================================================
            logger.info("CaseRetrieverWorkflow: Workflow execution completed")
            
            return {
                "case_retriever_state": case_retriever_state,
                "lower_citations": lower_citations,
                "upper_citations": upper_citations,
                "analysis_result": analysis_result,
            }
        
        except Exception as e:
            logger.error(f"CaseRetrieverWorkflow failed: {e}", exc_info=True)
            raise RuntimeError(f"Case retrieval workflow failed: {e}")
    
    def get_workflow_status(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract workflow execution status and summary.
        
        Args:
            result: Return dict from workflow execution
        
        Returns:
            Status summary
        """
        return {
            "workflow_completed": result.get("case_retriever_state", {}).get("workflow_status") == "completed",
            "lower_citations_found": len(result.get("lower_citations", [])),
            "upper_citations_found": len(result.get("upper_citations", [])),
            "analysis_generated": bool(result.get("analysis_result")),
        }
