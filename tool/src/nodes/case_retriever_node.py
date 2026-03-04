"""
Case Retriever Node for LangGraph workflow.

This node wraps the CaseRetrieverWorkflow and integrates it into the chat workflow.
"""

import logging
from typing import Any, Dict

from src.models import GraphState
from src.agents.case_retriever.workflow import CaseRetrieverWorkflow

logger = logging.getLogger(__name__)


def case_retriever_node(state: GraphState) -> Dict[str, Any]:
    """
    Node that executes the case retrieval workflow.
    
    Retrieves relevant cases from lower and upper courts, and performs
    comparative analysis to generate final recommendations.
    
    Args:
        state: GraphState from LangGraph
    
    Returns:
        Updated state with case retrieval results
    """
    try:
        logger.info("Executing Case Retriever Node")
        
        # Extract user query from state
        user_query = state.get("user_query", "")
        if not user_query:
            # Try to get from messages
            messages = state.get("messages", [])
            if messages and hasattr(messages[-1], "content"):
                user_query = messages[-1].content
        
        if not user_query:
            logger.warning("No user query found for case retrieval")
            return {
                "case_retriever_state": None,
                "messages": state.get("messages", [])
            }
        
        # Create workflow instance
        workflow = CaseRetrieverWorkflow()
        
        # Prepare state for workflow
        workflow_state = {
            "user_query": user_query
        }
        
        # Execute workflow
        result = workflow(workflow_state, callbacks=None)
        
        # Extract results
        case_retriever_state = result.get("case_retriever_state", {})
        analysis_result = result.get("analysis_result")
        
        logger.info(f"Case Retriever Node completed: {case_retriever_state.get('workflow_status')}")
        
        # Generate response message
        response_message = _create_response_message(analysis_result, case_retriever_state)
        
        # Update state
        return {
            "case_retriever_state": case_retriever_state,
            "analysis_result": analysis_result,
            "messages": state.get("messages", []) + [response_message] if response_message else state.get("messages", [])
        }
    
    except Exception as e:
        logger.error(f"Case Retriever Node failed: {e}", exc_info=True)
        
        # Return error state
        return {
            "case_retriever_state": {"error": str(e), "workflow_status": "failed"},
            "messages": state.get("messages", [])
        }


def _create_response_message(analysis_result: Any, case_retriever_state: Dict[str, Any]) -> Dict[str, str]:
    """
    Create a response message from case retrieval results.
    
    Args:
        analysis_result: CaseAnalysisResult from the analyzer
        case_retriever_state: Full state from workflow
    
    Returns:
        Dict with role and content for messages
    """
    if not analysis_result:
        return {
            "role": "assistant",
            "content": "Case retrieval completed but no analysis was generated. Please check your query."
        }
    
    # Build response from analysis
    message_parts = []
    
    # Summary
    if hasattr(analysis_result, "summary"):
        message_parts.append(f"**Case Analysis Summary:**\n{analysis_result.summary}")
    
    # Lower court cases
    if hasattr(analysis_result, "lower_court_cases"):
        num_cases = len(analysis_result.lower_court_cases)
        if num_cases > 0:
            message_parts.append(f"\n**Lower Court Cases ({num_cases} found):**")
            for case in analysis_result.lower_court_cases[:5]:  # Top 5
                message_parts.append(f"- {case.citation}: {case.court}")
    
    # Precedents
    if hasattr(analysis_result, "precedents"):
        num_precedents = len(analysis_result.precedents)
        if num_precedents > 0:
            message_parts.append(f"\n**Relevant Precedents ({num_precedents} found):**")
            for precedent in analysis_result.precedents[:5]:  # Top 5
                reversal_info = f" [REVERSED]" if precedent.reversal_status == "REVERSED" else ""
                message_parts.append(f"- {precedent.citation} ({precedent.court}){reversal_info}")
    
    # Reversals
    if hasattr(analysis_result, "reversals_identified"):
        num_reversals = len(analysis_result.reversals_identified)
        if num_reversals > 0:
            message_parts.append(f"\n**⚠️  Cases with Reversals ({num_reversals}):**")
            for reversal in analysis_result.reversals_identified[:3]:
                if reversal.get("lower_case"):
                    message_parts.append(f"- {reversal['lower_case']['citation']} was reversed at appellate level")
    
    # Legal principles
    if hasattr(analysis_result, "legal_principles_derived"):
        principles = analysis_result.legal_principles_derived
        if principles:
            message_parts.append(f"\n**Key Legal Principles:**")
            for principle in principles[:3]:
                message_parts.append(f"- {principle}")
    
    # Recommendations
    if hasattr(analysis_result, "recommendations"):
        message_parts.append(f"\n**Recommendations:**\n{analysis_result.recommendations}")
    
    # Confidence
    if hasattr(analysis_result, "confidence_score"):
        message_parts.append(f"\n**Analysis Confidence:** {analysis_result.confidence_score:.0%}")
    
    # Fallback
    if not message_parts:
        return {
            "role": "assistant",
            "content": "Case retrieval workflow completed. Please review the results in case_retriever_state."
        }
    
    return {
        "role": "assistant",
        "content": "\n".join(message_parts)
    }
