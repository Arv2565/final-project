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
            
            # Execute lower court finder
            lower_court_result = None
            lower_court_error = None
            try:
                lower_result_dict = self.lower_court_finder(state, callbacks=callbacks)
                lower_court_result = lower_result_dict.get("lower_court_result")
                logger.info("Lower court finder completed successfully")
            except Exception as e:
                lower_court_error = e
                logger.error(f"Lower court finder failed: {e}")
            
            # Execute upper court finder (can run in parallel with lower)
            logger.info("CaseRetrieverWorkflow: 📚 Analyzing precedents and appellate chains...")
            upper_court_result = None
            upper_court_error = None
            try:
                upper_result_dict = self.upper_court_finder(
                    lower_result=lower_court_result.dict() if lower_court_result else None,
                    state=state,
                    callbacks=callbacks
                )
                upper_court_result = upper_result_dict.get("upper_court_result")
                logger.info("Upper court finder completed successfully")
            except Exception as e:
                upper_court_error = e
                logger.error(f"Upper court finder failed: {e}")
            
            # Check if at least one finder succeeded
            if not lower_court_result and not upper_court_result:
                error_msg = "Both finders failed"
                if lower_court_error:
                    error_msg += f": Lower - {lower_court_error}"
                if upper_court_error:
                    error_msg += f"; Upper - {upper_court_error}"
                raise RuntimeError(error_msg)
            
            # ==================================================================
            # STAGE 2: LLM Synthesis (Sequential on Finder Results)
            # ==================================================================
            logger.info("CaseRetrieverWorkflow: Stage 2 - Running comparative analyzer")
            logger.info("CaseRetrieverWorkflow: ⚖️ Generating case summary and conclusion...")
            
            analysis_result = None
            analysis_error = None
            
            if lower_court_result and upper_court_result:
                try:
                    analyzer_result_dict = self.analyzer(
                        lower_result=lower_court_result,
                        upper_result=upper_court_result,
                        state=state,
                        callbacks=callbacks
                    )
                    analysis_result = analyzer_result_dict.get("analysis_result")
                    logger.info("Comparative analyzer completed successfully")
                except Exception as e:
                    analysis_error = e
                    logger.error(f"Comparative analyzer failed: {e}")
            else:
                logger.warning(
                    "Skipping analysis - missing finder results. "
                    f"Have lower: {bool(lower_court_result)}, upper: {bool(upper_court_result)}"
                )
            
            # ==================================================================
            # STAGE 3: Accumulate Results into State
            # ==================================================================
            logger.info("CaseRetrieverWorkflow: Stage 3 - Accumulating results")
            
            case_retriever_state = {
                "lower_court_cases": lower_court_result.dict() if lower_court_result else None,
                "upper_court_precedents": upper_court_result.dict() if upper_court_result else None,
                "case_analysis": analysis_result.dict() if analysis_result else None,
                "workflow_status": "completed" if (lower_court_result and upper_court_result) else "partial",
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
                "lower_court_result": lower_court_result,
                "upper_court_result": upper_court_result,
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
            "lower_court_cases_found": len(result.get("lower_court_result", {}).get("cases", [])) if result.get("lower_court_result") else 0,
            "precedents_found": len(result.get("upper_court_result", {}).get("precedents", [])) if result.get("upper_court_result") else 0,
            "analysis_generated": bool(result.get("analysis_result")),
        }
