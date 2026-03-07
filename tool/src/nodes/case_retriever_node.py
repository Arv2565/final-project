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
    
    Retrieves relevant cases from lower and upper courts, then generates
    an LLM summary in markdown and relevant PDF paths.
    
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
        
        # Extract markdown and PDF paths from synthesis result
        analysis_markdown = _extract_markdown(analysis_result)
        case_pdf_paths = _extract_pdf_paths(analysis_result)
        
        logger.info(f"Case Retriever Node completed: {case_retriever_state.get('workflow_status')} - Found {len(case_pdf_paths)} PDFs")
        
        # Generate response message
        response_message = _create_response_message(analysis_result, case_retriever_state)
        
        # Update state
        return {
            "case_retriever_state": case_retriever_state,
            "analysis_result": analysis_result,
            "case_retriever_markdown": analysis_markdown,
            "case_pdf_paths": case_pdf_paths,
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
        analysis_result: CaseSynthesisResult from the analyzer
        case_retriever_state: Full state from workflow
    
    Returns:
        Dict with role and content for messages
    """
    if not analysis_result:
        return {
            "role": "assistant",
            "content": "Case retrieval completed but no analysis was generated. Please check your query."
        }
    
    markdown = _extract_markdown(analysis_result)
    if not markdown:
        return {
            "role": "assistant",
            "content": "Case retrieval workflow completed but no markdown analysis was generated."
        }

    return {
        "role": "assistant",
        "content": markdown
    }


def _extract_markdown(analysis_result: Any) -> str:
    """Extract markdown summary from synthesis result."""
    if not analysis_result:
        logger.warning("Analysis result is None")
        return ""
    try:
        if hasattr(analysis_result, "analysis_markdown"):
            md = analysis_result.analysis_markdown
            if md and isinstance(md, str):
                logger.info(f"Extracted markdown: {len(md)} chars")
                return md
        logger.warning("Analysis result missing or empty analysis_markdown field")
        return ""
    except Exception as e:
        logger.error(f"Error extracting markdown: {e}")
        return ""


def _extract_pdf_paths(analysis_result: Any) -> list:
    """
    Extract unique PDF paths from CaseSynthesisResult.
    
    Args:
        analysis_result: CaseSynthesisResult object from the analyzer
    
    Returns:
        List of unique PDF paths
    """
    pdf_paths = set()
    
    if not analysis_result:
        logger.warning("Analysis result is None for PDF extraction")
        return []
    
    try:
        if hasattr(analysis_result, "relevant_pdf_paths"):
            paths = analysis_result.relevant_pdf_paths
            if paths and isinstance(paths, list):
                for path in paths:
                    if path and isinstance(path, str):
                        pdf_paths.add(path)
                logger.info(f"Extracted {len(pdf_paths)} unique PDF paths")
        else:
            logger.warning("Analysis result missing relevant_pdf_paths field")
    except Exception as e:
        logger.error(f"Error extracting PDF paths: {e}")
    
    return sorted(list(pdf_paths))
