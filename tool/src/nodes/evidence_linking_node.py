from typing import Dict, Any, List, Optional, TYPE_CHECKING

from langchain_core.runnables import RunnableConfig

from src.models import GraphState
from src.agents.activity_law.evidence_linking import EvidenceLinkingAgent
from src.config.observability import get_langfuse_callback
from src.models.activity_law import ActivityLawState


# Lazy initialization
_evidence_linking_agent = None
_callback_handler = None
_callbacks_initialized = False


def evidence_linking_node(state: GraphState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    """LangGraph node that delegates to EvidenceLinkingAgent.
    
    This node links facts and documents to the compliance assessment.
    
    Args:
        state: GraphState
        config: Runtime configuration containing callbacks
        
    Returns:
        State update with 'activity_law_state.evidence_linking'
    """
    global _evidence_linking_agent
    
    if _evidence_linking_agent is None:
        _evidence_linking_agent = EvidenceLinkingAgent()
        
    callbacks = config.get("callbacks", []) if config else []
    result = _evidence_linking_agent(state, callbacks=callbacks)
    
    # Update nested state
    current_activity_state = state.get("activity_law_state", ActivityLawState())
    if result and result.get("evidence_linking"):
        current_activity_state.evidence_linking = result["evidence_linking"]
        
    return {**state, "activity_law_state": current_activity_state}
