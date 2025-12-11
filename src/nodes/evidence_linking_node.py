from typing import Dict, Any, List

from src.models import GraphState
from src.agents.activity_law.evidence_linking import EvidenceLinkingAgent
from src.config.observability import get_langfuse_callback
from src.models.activity_law import ActivityLawState


# Lazy initialization
_evidence_linking_agent = None
_callback_handler = None
_callbacks_initialized = False


def evidence_linking_node(state: GraphState) -> Dict[str, Any]:
    """LangGraph node that delegates to EvidenceLinkingAgent.
    
    This node links facts and documents to the compliance assessment.
    
    Args:
        state: GraphState
        
    Returns:
        State update with 'activity_law_state.evidence_linking'
    """
    global _evidence_linking_agent
    global _callback_handler
    global _callbacks_initialized
    
    if _evidence_linking_agent is None:
        _evidence_linking_agent = EvidenceLinkingAgent()
        
    if not _callbacks_initialized:
        _callback_handler = get_langfuse_callback()
        _callbacks_initialized = True
        
    callbacks = [_callback_handler] if _callback_handler else []
    result = _evidence_linking_agent(state, callbacks=callbacks)
    
    # Update nested state
    current_activity_state = state.get("activity_law_state", ActivityLawState())
    if result and result.get("evidence_linking"):
        current_activity_state.evidence_linking = result["evidence_linking"]
        
    return {"activity_law_state": current_activity_state}
